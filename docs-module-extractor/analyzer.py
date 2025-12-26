import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import config
from utils import CacheManager, chunk_content

# ---------------- LOGGING SETUP ----------------
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ---------------- OPTIONAL IMPORTS ----------------
try:
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class ModuleAnalyzer:
    """Analyzes documentation to identify modules and submodules."""

    def __init__(self, use_llm: bool = False):
        self.cache = CacheManager()
        self.use_llm = use_llm and LLM_AVAILABLE

        if self.use_llm and config.OPENAI_API_KEY:
            self.llm = ChatOpenAI(
                model_name=config.LLM_MODEL,
                temperature=config.LLM_TEMPERATURE,
                openai_api_key=config.OPENAI_API_KEY
            )
        else:
            self.llm = None

        if EMBEDDINGS_AVAILABLE:
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        else:
            self.embedder = None

    # ---------------- MAIN PIPELINE ----------------
    def analyze_documentation(self, parsed_pages: List[Dict]) -> List[Dict]:
        all_content = self.combine_content(parsed_pages)
        candidate_modules = self.extract_candidate_modules(parsed_pages)
        clustered_modules = self.cluster_modules(candidate_modules)
        modules_with_descriptions = self.generate_descriptions(
            clustered_modules, all_content
        )
        return self.format_output(modules_with_descriptions)

    # ---------------- CONTENT HANDLING ----------------
    def combine_content(self, parsed_pages: List[Dict]) -> str:
        combined = []
        for page in parsed_pages:
            combined.append(page.get("metadata", {}).get("title", ""))
            combined.append(page.get("content", ""))
        return " ".join(combined)

    # ---------------- MODULE EXTRACTION ----------------
    def extract_candidate_modules(self, parsed_pages: List[Dict]) -> List[Dict]:
        candidates = []

        for page in parsed_pages:
            title = page.get("metadata", {}).get("title", "")
            if title and len(title) > 3:
                candidates.append({
                    "name": title,
                    "source": "title",
                    "content": page.get("content", ""),
                    "url": page.get("url", "")
                })

            headings = page.get("structure", {}).get("headings", {})
            for level in ["h1", "h2", "h3"]:
                for heading in headings.get(level, []):
                    if heading and len(heading) > 3:
                        candidates.append({
                            "name": heading,
                            "source": f"heading_{level}",
                            "content": self.get_section_content(heading, page),
                            "url": page.get("url", "")
                        })

            breadcrumbs = page.get("metadata", {}).get("breadcrumbs", [])
            for i, crumb in enumerate(breadcrumbs):
                if crumb and len(crumb) > 3:
                    candidates.append({
                        "name": crumb,
                        "source": f"breadcrumb_{i}",
                        "content": page.get("content", ""),
                        "url": page.get("url", "")
                    })

        return candidates

    def get_section_content(self, heading: str, page: Dict) -> str:
        sections = page.get("structure", {}).get("sections", [])
        for section in sections:
            if section.get("title", "").lower() == heading.lower():
                return section.get("content", "")
        return page.get("content", "")

    # ---------------- CLUSTERING ----------------
    def cluster_modules(self, candidates: List[Dict]) -> List[Dict]:
        if not candidates:
            return []

        names = [c["name"] for c in candidates]

        if self.embedder:
            embeddings = self.embedder.encode(names)
            similarity_matrix = cosine_similarity(embeddings)
            clustering = DBSCAN(
                eps=0.5,
                min_samples=2,
                metric="precomputed"
            ).fit(1 - similarity_matrix)

            clusters = {}
            for idx, label in enumerate(clustering.labels_):
                if label == -1:
                    continue
                clusters.setdefault(label, []).append(candidates[idx])

            return [self.choose_main_module(v) for v in clusters.values()]

        # TF-IDF fallback
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            tfidf = vectorizer.fit_transform(names)
            similarity = cosine_similarity(tfidf)

            unique = []
            seen = set()
            for i, name in enumerate(names):
                if name.lower() not in seen:
                    seen.add(name.lower())
                    unique.append(candidates[i])
            return unique

        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return candidates

    def choose_main_module(self, candidates: List[Dict]) -> Dict:
        priority = {
            "title": 0,
            "heading_h1": 1,
            "heading_h2": 2,
            "heading_h3": 3
        }

        candidates.sort(key=lambda x: (
            priority.get(x["source"], 99),
            -len(x.get("content", ""))
        ))
        return candidates[0]

    # ---------------- DESCRIPTION GENERATION ----------------
    def generate_descriptions(self, modules: List[Dict], all_content: str) -> List[Dict]:
        result = []

        for module in modules:
            if self.use_llm and self.llm:
                description = self.generate_description_with_llm(module, all_content)
            else:
                description = self.generate_description_algorithmic(module, all_content)

            submodules = self.extract_submodules(module, all_content)

            result.append({
                "module": module["name"],
                "description": description,
                "submodules": submodules,
                "confidence": self.calculate_confidence(module, description)
            })

        return result

    def generate_description_with_llm(self, module: Dict, context: str) -> str:
        prompt = PromptTemplate(
            input_variables=["module_name", "module_content", "context"],
            template="""
            Generate a concise description for the module "{module_name}"
            using the documentation below.

            Module Content:
            {module_content}

            Context:
            {context}

            Description:
            """
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)

        try:
            response = chain.run(
                module_name=module["name"],
                module_content=module["content"][:2000],
                context=context[:3000]
            )
            return response.strip()
        except Exception as e:
            logger.error(f"LLM description generation failed: {e}")
            return self.generate_description_algorithmic(module, context)

    def generate_description_algorithmic(self, module: Dict, context: str) -> str:
        name = module["name"]
        content = module.get("content", "")

        sentences = self.extract_relevant_sentences(name, content)
        if not sentences:
            sentences = self.extract_relevant_sentences(name, context)

        if sentences:
            return f"{name}: " + " ".join(sentences[:3])[:500]

        return f"Module related to {name} functionality."

    # ---------------- SUBMODULES ----------------
    def extract_relevant_sentences(self, topic: str, text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        topic_words = set(topic.lower().split())

        relevant = []
        for s in sentences:
            s_words = set(s.lower().split())
            if topic.lower() in s.lower() or len(topic_words & s_words) >= 2:
                relevant.append(s)

        return relevant[:5]

    def extract_submodules(self, module: Dict, context: str) -> Dict[str, str]:
        submodules = {}
        content = module.get("content", "")

        candidates = self.extract_potential_submodules(content)
        for name in candidates[:config.MAX_SUBMODULES_PER_MODULE]:
            desc = self.generate_submodule_description(name, content, context)
            if desc:
                submodules[name] = desc

        return submodules

    def extract_potential_submodules(self, content: str) -> List[str]:
        patterns = [
            r'includes\s+(.+?)(?:\.|$)',
            r'such as\s+(.+?)(?:\.|$)',
            r'including\s+(.+?)(?:\.|$)'
        ]

        found = []
        for p in patterns:
            matches = re.findall(p, content, re.IGNORECASE)
            for match in matches:
                items = re.split(r',|\band\b|\bor\b', match)
                found.extend(i.strip().title() for i in items if len(i.strip()) > 3)

        return list(dict.fromkeys(found))

    def generate_submodule_description(self, submodule: str, content: str, context: str) -> str:
        sentences = self.extract_relevant_sentences(submodule, content)
        if not sentences:
            sentences = self.extract_relevant_sentences(submodule, context)

        if sentences:
            return " ".join(sentences[:2])[:200]

        return f"Functionality related to {submodule}."

    # ---------------- CONFIDENCE ----------------
    def calculate_confidence(self, module: Dict, description: str) -> float:
        score = 0.5

        if len(module.get("content", "")) > 800:
            score += 0.2
        if len(description) > 100:
            score += 0.1
        if module.get("source") == "title":
            score += 0.1

        return min(score, 1.0)

    # ---------------- OUTPUT ----------------
    def format_output(self, modules: List[Dict]) -> List[Dict]:
        return [
            {
                "module": m["module"],
                "Description": m["description"],
                "Submodules": m["submodules"],
                "confidence_score": m["confidence"]
            }
            for m in modules
        ]
