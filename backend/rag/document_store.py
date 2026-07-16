"""RAG Document Store — BM25 + 德国法原文检索（带磁盘缓存）"""

import json, re, pickle, logging, time
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
CACHE_FILE = DATA_DIR / "bm25_index_cache.pkl"
CACHE_VERSION = 2  # bump to invalidate old caches


class DocumentStore:
    """BM25 法律文档检索（德国法原文 + 内置知识库）"""

    def __init__(self):
        self.collection = None
        self.embedding_fn = None
        self.documents = []
        self.bm25 = None
        self.tokenized_corpus = []
        self._initialized = False

    async def initialize(self):
        """初始化：优先从缓存加载，避免重复索引"""
        if self._load_from_cache():
            self._initialized = True
            return

        t0 = time.time()
        self._build_builtin_documents()
        self._load_german_law_documents()
        self._build_bm25_index()
        self._save_to_cache()

        self._initialized = True
        stats = self.get_stats()
        logger.info(f"DocumentStore built in {time.time()-t0:.1f}s: "
                    f"{stats['total_documents']} docs, {stats['total_chars']:,} chars")

    def _cache_key(self) -> str:
        """Generate cache key based on German law file modification times"""
        from backend.rag.german_law_loader import LAW_FILES, LAW_DIR
        parts = [str(CACHE_VERSION)]
        for label, fname in sorted(LAW_FILES.items()):
            fp = LAW_DIR / fname
            if fp.exists():
                parts.append(f"{label}:{fp.stat().st_mtime}")
        return "|".join(parts)

    def _load_from_cache(self) -> bool:
        """Try to load BM25 index from disk cache"""
        if not CACHE_FILE.exists():
            return False
        try:
            with open(CACHE_FILE, "rb") as f:
                data = pickle.load(f)
            if data.get("cache_key") != self._cache_key():
                logger.info("BM25 cache stale, rebuilding...")
                return False
            self.documents = data["documents"]
            self.tokenized_corpus = data["tokenized_corpus"]
            from rank_bm25 import BM25Okapi
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            self._initialized = True
            stats = self.get_stats()
            logger.info(f"BM25 loaded from cache: {stats['total_documents']} docs, "
                        f"{stats['total_chars']:,} chars")
            return True
        except Exception as e:
            logger.warning(f"BM25 cache load failed: {e}")
            return False

    def _save_to_cache(self):
        """Save BM25 index to disk"""
        if not self.bm25 or not self.documents:
            return
        try:
            data = {
                "cache_key": self._cache_key(),
                "documents": self.documents,
                "tokenized_corpus": self.tokenized_corpus,
            }
            with open(CACHE_FILE, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            size_mb = CACHE_FILE.stat().st_size / (1024 * 1024)
            logger.info(f"BM25 cache saved: {size_mb:.1f}MB")
        except Exception as e:
            logger.warning(f"BM25 cache save failed: {e}")

    def _build_builtin_documents(self):
        """构建内置中德税收法律知识文档"""
        docs = []

        # 1. Rules
        with open(DATA_DIR / "rules.json", "r", encoding="utf-8") as f:
            rules = json.load(f)
        for gid, group in rules["groups"].items():
            docs.append({
                "id": f"rule_group_{gid}",
                "text": f"{group['title']}：{group['description']}。法律依据：{group['legal_basis']}",
                "source": "rules.json", "type": "pe_classification",
            })
        for qid, q in rules["questions"].items():
            docs.append({
                "id": f"rule_q{qid}",
                "text": f"PE判定要件Q{qid}：{q['text']}。{q.get('help', '')}。法律依据：{q.get('legal_ref', '')}",
                "source": "rules.json", "type": "legal_requirement",
            })

        # 2. Legal provisions
        with open(DATA_DIR / "legal_basis.json", "r", encoding="utf-8") as f:
            legal = json.load(f)
        for pid, prov in legal["provisions"].items():
            docs.append({
                "id": f"legal_{pid}",
                "text": f"{prov['title']}：{prov['content']}。来源：{prov['source']}",
                "source": "legal_basis.json", "type": "legal_provision",
            })

        # 3. HGB checklist
        with open(DATA_DIR / "hgb_checklist.json", "r", encoding="utf-8") as f:
            hgb = json.load(f)
        for level_id, level_data in hgb["levels"].items():
            for section in level_data["sections"]:
                for item in section["items"]:
                    docs.append({
                        "id": f"hgb_{level_id}_{item['task'][:30]}",
                        "text": f"PE风险等级{level_data['label']}·{section['title']}：{item['task']}。法律依据：{item['legal']}。期限：{item['deadline']}",
                        "source": "hgb_checklist.json", "type": "hgb_compliance",
                    })

        # 4. Builtin treaty fulltext
        builtin_texts = [
            ("pe_treaty_full", "中德协定第5条全文",
             """中德税收协定第5条常设机构：第1款常设机构指企业进行全部或部分营业的固定营业场所。
第2款特别包括管理场所分支机构办事处工厂作业场所矿场油井气井采石场等。
第3款建筑工地建筑装配或安装工程或相关监督管理活动连续超过12个月构成常设机构。
第4款不包括专为存储陈列交付货物目的使用的设施、专为存储陈列交付目的保存货物库存、
专为委托加工目的保存货物库存、专为企业采购货物或收集信息设立的固定营业场所、
专为本企业进行其他准备性或辅助性活动的固定营业场所。
第5款非独立代理人有权以企业名义签订合同并经常行使该权力时构成常设机构。
第6款独立代理人经纪人佣金代理人等按常规经营业务时不构成常设机构。"""),
            ("beps_action7", "BEPS行动7摘要",
             """BEPS第7项行动计划防止人为规避常设机构认定：第一代理人PE门槛降低将有权以企业名义
签订合同扩展为在订立合同过程中起主要作用且企业通常不对合同进行实质性修改。
第二准备性辅助性豁免收紧引入反碎片化规则多处关联场所组合活动不豁免紧密关联企业活动合并审查。
第三合同拆分反避税同一项目多个关联合同合并计算工期。"""),
            ("ao_pe_definition", "德国AO PE定义",
             """德国租税通则AO第12条常设机构指服务于企业经营活动的任何固定营业设施或设备。
尤其包括经营管理场所分支机构营业处所制造或工场仓库采购或销售处矿山采石场
其他固定递进或浮动的自然资源开采场所持续超过6个月的建筑或安装工程。
AO第13条常设代理人与企业存在常设代理人关系的人为该企业开展活动并以其名义缔结交易构成常设机构。
重要提示双边协定中德协定12个月工程门槛优先于德国国内法AO 6个月工程门槛。"""),
        ]
        for doc_id, title, text in builtin_texts:
            docs.append({"id": doc_id, "text": f"{title}：{text.strip()}",
                         "source": "builtin", "type": "treaty_fulltext"})

        self.documents = docs

    def _load_german_law_documents(self):
        """加载德国法原文 PDF/EPUB（如可用）"""
        try:
            from backend.rag.german_law_loader import GermanLawLoader
            loader = GermanLawLoader()
            german_docs = loader.load_all()
            if german_docs:
                logger.info(f"Loaded {len(german_docs)} German law chunks")
                self.documents.extend(german_docs)
                stats = loader.get_stats(german_docs)
                for law, count in sorted(stats.get("by_law", {}).items()):
                    logger.info(f"  {law}: {count} chunks")
            else:
                logger.warning("No German law documents loaded")
        except Exception as e:
            logger.warning(f"German law loading skipped: {e}")

    def _build_bm25_index(self):
        """构建 BM25 索引"""
        if len(self.documents) < 3:
            return

        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.warning("rank_bm25 not installed, using keyword search")
            return

        # Tokenize: split on whitespace + Chinese characters
        def tokenize(text):
            # Split Chinese characters individually, keep word tokens
            tokens = []
            for part in re.split(r'(\s+)', text):
                part = part.strip()
                if not part:
                    continue
                # Check if mostly Chinese
                chinese_chars = len(re.findall(r'[一-鿿]', part))
                if chinese_chars > len(part) * 0.5:
                    tokens.extend(list(part))  # character-level for Chinese
                else:
                    tokens.extend(part.lower().split())
            return tokens

        self.tokenized_corpus = [tokenize(d["text"]) for d in self.documents]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        logger.info(f"BM25 index built: {len(self.tokenized_corpus)} documents")

    def _init_with_chromadb(self):
        """ChromaDB vector store — skipped for offline use (BM25 is primary)"""
        # BM25 is the primary retriever; ChromaDB requires network for embedding models
        # Skipping to keep the system fully offline-capable
        logger.info("ChromaDB skipped — BM25 is primary retriever (offline-capable)")

    def search(self, query: str, top_k: int = 5, filters: dict = None) -> list:
        """混合检索：BM25 为主，向量检索为辅"""
        if self.bm25:
            return self._bm25_search(query, top_k, filters)
        return self._keyword_search(query, top_k, filters)

    def _bm25_search(self, query: str, top_k: int, filters: dict) -> list:
        """BM25 检索"""
        def tokenize(text):
            tokens = []
            for part in re.split(r'(\s+)', text):
                part = part.strip()
                if not part:
                    continue
                chinese_chars = len(re.findall(r'[一-鿿]', part))
                if chinese_chars > len(part) * 0.5:
                    tokens.extend(list(part))
                else:
                    tokens.extend(part.lower().split())
            return tokens

        query_tokens = tokenize(query)
        scores = self.bm25.get_scores(query_tokens)

        # Build scored results
        scored = []
        for i, score in enumerate(scores):
            if score <= 0:
                continue
            doc = self.documents[i]

            # Apply type filter
            if filters and "type" in filters:
                if doc.get("type") != filters["type"]:
                    continue

            # Normalize score to 0-1 range (rough)
            norm_score = min(score / max(1, max(scores)), 1.0)
            scored.append({
                "content": doc["text"][:400],
                "source": doc.get("source", "unknown"),
                "type": doc.get("type", ""),
                "score": round(norm_score, 4),
                "doc_id": doc.get("id", ""),
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _keyword_search(self, query: str, top_k: int, filters: dict) -> list:
        """关键词回退检索"""
        keywords = set(re.findall(r'[\w一-鿿]{2,}', query.lower()))
        scored = []
        for doc in self.documents:
            if filters and "type" in filters:
                if doc.get("type") != filters["type"]:
                    continue
            text_lower = doc["text"].lower()
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scored.append({
                    "content": doc["text"][:400],
                    "source": doc.get("source", "unknown"),
                    "type": doc.get("type", ""),
                    "score": round(score / max(len(keywords), 1), 4),
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def get_document_by_id(self, doc_id: str):
        for doc in self.documents:
            if doc["id"] == doc_id:
                return doc
        return None

    def get_stats(self) -> dict:
        total_chars = sum(len(d["text"]) for d in self.documents)
        sources = list(set(d.get("source", "unknown") for d in self.documents))
        types = list(set(d.get("type", "") for d in self.documents))
        return {
            "total_documents": len(self.documents),
            "total_chars": total_chars,
            "sources": sources,
            "types": types,
            "has_bm25": self.bm25 is not None,
            "has_chromadb": self.collection is not None,
        }

    def close(self):
        if self.collection:
            self.collection = None
        self.documents = []
        self.bm25 = None
