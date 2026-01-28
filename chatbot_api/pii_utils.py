import spacy
import re
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel, Field
from rag_utils import ollama_llm
import re
import os

class Language(BaseModel):
    """Pydantic model for language detection response"""
    language: str = Field(description="Detected language code, e.g., 'en' or 'fr'")
    confidence: float = Field(description="Confidence level of the detected language")

class BilingualPIIDetector:
    def __init__(self):
        # Load both English and French models
        try:
            self.nlp_en = spacy.load("en_core_web_sm")
        except OSError:
            raise OSError("English spaCy model not found. Run: python -m spacy download en_core_web_sm")
        
        try:
            self.nlp_fr = spacy.load("fr_core_news_sm")
        except OSError:
            raise OSError("French spaCy model not found. Run: python -m spacy download fr_core_news_sm")
        
        self.llm = ollama_llm

        # MINIMALIST PII labels - only truly confidential personal information
        self.sensitive_labels_en = {
            'PERSON',  # Only person names (not organizations, locations, etc.)
        }
        
        self.sensitive_labels_fr = {
            'PER',     # Only person names (French equivalent)
        }
        
        # Custom regex patterns for high-confidence personal identifiers
        self.regex_patterns = {
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'PHONE': r'(\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            'SSN': r'\b\d{3}-\d{2}-\d{4}\b',
            'CREDIT_CARD': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            'FRENCH_SSN': r'\b[12]\d{12}\b',
            'PASSPORT': r'\b[A-Z]{1,2}\d{6,9}\b',  # Passport numbers
        }

    def detect_language(self, text: str) -> str:
        prompt = f"""
        Analyze the following text and determine if it's primarily in English or French.
        Return ONLY a JSON object with the exact structure:
        {{
            "language": "english" or "french",
            "confidence": 0.95
        }}
        
        Text to analyze: "{text}"
        
        Consider:
        - Vocabulary and word patterns
        - Grammar structure
        - Common phrases and expressions
        - Language-specific characters or accents
        
        Return only the language used in the text.
        """

        response = self.llm.with_structured_output(Language,method="json_schema").invoke(prompt)
        # print(f"language detected : {response.language}, detection confidence: {response.confidence}")
        
        return response.language
        
    
    def detect_pii_entities(self, text: str) -> List[Dict]:
        """Detect only truly confidential PII in text"""
        if not text or not text.strip():
            return []
            
        language = self.detect_language(text)
        
        if language == 'en':
            doc = self.nlp_en(text)
            sensitive_labels = self.sensitive_labels_en
        else:
            doc = self.nlp_fr(text)
            sensitive_labels = self.sensitive_labels_fr
        
        entities = []
        
        # Detect using spaCy NER - only person names
        for ent in doc.ents:
            if (ent.label_ in sensitive_labels and 
                len(ent.text.strip()) > 2 and  # Minimum length to avoid partial words
                not ent.text.isspace()):       # Avoid whitespace entities
                entities.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'source': 'spacy',
                    'language': language
                })
        
        # Detect using regex patterns for high-confidence personal identifiers
        for pattern_name, pattern in self.regex_patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Check if this match overlaps with any existing entity
                overlap = False
                for entity in entities:
                    if not (match.end() <= entity['start'] or match.start() >= entity['end']):
                        overlap = True
                        break
                
                if not overlap:
                    entities.append({
                        'text': match.group(),
                        'label': pattern_name,
                        'start': match.start(),
                        'end': match.end(),
                        'source': 'regex',
                        'language': language
                    })
        
        # Remove duplicates and sort by start position
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity['text'], entity['start'], entity['end'])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        return sorted(unique_entities, key=lambda x: x['start'])

    def redact_pii(self, text: str, strategy: str = "redact") -> Tuple[str, List[Dict]]:
        """Redact only confidential PII from text"""
        entities = self.detect_pii_entities(text)
        redacted_text = text
        
        # Process in reverse to maintain string positions
        for entity in sorted(entities, key=lambda x: x['start'], reverse=True):
            replacement = self._get_replacement(entity, strategy)
            redacted_text = (
                redacted_text[:entity['start']] + 
                replacement + 
                redacted_text[entity['end']:]
            )
        
        return redacted_text, entities

    def _get_replacement(self, entity: Dict, strategy: str) -> str:
        """Get replacement text based on strategy"""
        if strategy == "redact":
            return f"[REDACTED_{entity['label']}]"
        elif strategy == "mask":
            if entity['label'] in ['EMAIL', 'PHONE']:
                text = entity['text']
                if '@' in text:  # Email
                    parts = text.split('@')
                    return f"{parts[0][:2]}***@{parts[1]}"
                else:  # Phone
                    return f"***-***-{text[-4:]}" if len(text) > 4 else "***"
            else:
                return f"***{entity['label']}***"
        elif strategy == "block":
            raise ValueError(f"Confidential information detected and blocked: {entity['label']} - {entity['text']}")
        else:
            return f"[REDACTED_{entity['label']}]"

    def contains_pii(self, text: str) -> bool:
        """Check if text contains confidential PII"""
        return len(self.detect_pii_entities(text)) > 0

    def get_pii_summary(self, text: str) -> Dict:
        """Get a summary of detected confidential information"""
        entities = self.detect_pii_entities(text)
        safe_text, _ = self.redact_pii(text)
        
        return {
            'has_confidential_info': len(entities) > 0,
            'entities_found': len(entities),
            'entity_types': list(set(entity['label'] for entity in entities)),
            'safe_text': safe_text,
            'details': entities
        }

# Global instance
pii_detector = BilingualPIIDetector()

# Convenience functions
def detect_pii(text: str) -> List[Dict]:
    """Detect only confidential PII in text"""
    return pii_detector.detect_pii_entities(text)

def redact_pii(text: str, strategy: str = "redact") -> Tuple[str, List[Dict]]:
    """Redact only confidential PII from text"""
    return pii_detector.redact_pii(text, strategy)

def contains_pii(text: str) -> bool:
    """Check if text contains confidential PII"""
    return pii_detector.contains_pii(text)

def get_pii_report(text: str) -> Dict:
    """Get a detailed report of confidential information detected"""
    return pii_detector.get_pii_summary(text)

