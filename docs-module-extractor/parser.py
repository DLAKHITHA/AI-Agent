import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from config import config
from utils import clean_text, extract_headings_from_html


class DocumentationParser:
    """Parses HTML documentation content into structured format."""
    
    def __init__(self):
        self.heading_patterns = [
            (r'(?i)^(chapter|part|module)\s+\d+[.:]\s*(.+)$', 1),
            (r'(?i)^\d+[.]\d+\s+.+$', 2),  # 1.1 Title
            (r'(?i)^\d+[.]\d+[.]\d+\s+.+$', 3),  # 1.1.1 Title
            (r'(?i)^[A-Z][.]\s+.+$', 2),  # A. Title
            (r'(?i)^[ivx]+[.)]\s+.+$', 2),  # i. Title
        ]
    
    def parse_page(self, url: str, html: str, content: str) -> Dict:
        """Parse a single documentation page."""
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract metadata
        metadata = self.extract_metadata(soup, url)
        
        # Extract structure
        structure = self.extract_structure(soup, content)
        
        # Extract topics
        topics = self.extract_topics(content)
        
        return {
            'url': url,
            'metadata': metadata,
            'structure': structure,
            'topics': topics,
            'content': content,
            'clean_content': self.clean_documentation_content(content)
        }
    
    def extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract metadata from page."""
        metadata = {
            'url': url,
            'title': '',
            'description': '',
            'keywords': [],
            'breadcrumbs': [],
            'last_modified': None
        }
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = clean_text(title_tag.text)
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            metadata['description'] = clean_text(meta_desc['content'])
        
        # Extract meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            keywords = meta_keywords['content'].split(',')
            metadata['keywords'] = [clean_text(k) for k in keywords]
        
        # Extract breadcrumbs
        metadata['breadcrumbs'] = self.extract_breadcrumbs(soup)
        
        # Extract last modified (if available)
        metadata['last_modified'] = self.extract_last_modified(soup)
        
        return metadata
    
    def extract_breadcrumbs(self, soup: BeautifulSoup) -> List[str]:
        """Extract breadcrumb navigation."""
        breadcrumbs = []
        
        # Common breadcrumb selectors
        selectors = [
            '.breadcrumb', '.breadcrumbs', '.bc', 
            '[aria-label="breadcrumb"]', '.nav-path'
        ]
        
        for selector in selectors:
            breadcrumb_elem = soup.select_one(selector)
            if breadcrumb_elem:
                items = breadcrumb_elem.find_all(['li', 'span', 'a'])
                for item in items:
                    text = clean_text(item.text)
                    if text and text.lower() not in ['home', 'main']:
                        breadcrumbs.append(text)
                break
        
        return breadcrumbs
    
    def extract_last_modified(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract last modified date if available."""
        # Common patterns for last modified
        patterns = [
            r'last\s*(?:updated|modified)[:\s]*([\w\s,]+)',
            r'updated\s*:\s*([\w\s,]+)',
            r'version.*(\d{4}[-/]\d{1,2}[-/]\d{1,2})'
        ]
        
        # Search in meta tags first
        meta_date = soup.find('meta', attrs={'name': 'last-modified'})
        if meta_date and meta_date.get('content'):
            return meta_date['content']
        
        # Search in content
        all_text = soup.get_text()
        for pattern in patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_structure(self, soup: BeautifulSoup, content: str) -> Dict:
        """Extract document structure from headings and sections."""
        structure = {
            'headings': extract_headings_from_html(str(soup)),
            'sections': [],
            'tables': [],
            'lists': []
        }
        
        # Extract sections based on headings
        structure['sections'] = self.extract_sections(soup)
        
        # Extract tables
        structure['tables'] = self.extract_tables(soup)
        
        # Extract lists
        structure['lists'] = self.extract_lists(soup)
        
        return structure
    
    def extract_sections(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract document sections."""
        sections = []
        
        # Find all heading elements
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for i, heading in enumerate(headings):
            section_content = []
            next_elem = heading.find_next_sibling()
            
            # Collect content until next heading of same or higher level
            while next_elem and next_elem.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                text = clean_text(next_elem.get_text())
                if text:
                    section_content.append(text)
                next_elem = next_elem.find_next_sibling()
            
            sections.append({
                'level': int(heading.name[1]),
                'title': clean_text(heading.get_text()),
                'content': ' '.join(section_content),
                'id': heading.get('id', f'section-{i}')
            })
        
        return sections
    
    def extract_tables(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract tables from documentation."""
        tables = []
        
        for i, table in enumerate(soup.find_all('table')):
            rows = []
            
            # Extract table headers
            headers = []
            thead = table.find('thead')
            if thead:
                for th in thead.find_all(['th', 'td']):
                    headers.append(clean_text(th.get_text()))
            
            # Extract table rows
            tbody = table.find('tbody') or table
            for tr in tbody.find_all('tr'):
                cells = []
                for td in tr.find_all(['td', 'th']):
                    cells.append(clean_text(td.get_text()))
                
                if cells:
                    rows.append(cells)
            
            if rows:
                tables.append({
                    'id': f'table-{i}',
                    'headers': headers,
                    'rows': rows,
                    'caption': self.extract_table_caption(table)
                })
        
        return tables
    
    def extract_table_caption(self, table: BeautifulSoup) -> str:
        """Extract table caption if available."""
        caption = table.find('caption')
        if caption:
            return clean_text(caption.get_text())
        
        # Look for preceding paragraph as caption
        prev_elem = table.find_previous_sibling(['p', 'div', 'h3', 'h4'])
        if prev_elem:
            text = clean_text(prev_elem.get_text())
            if text and len(text) < 200:  # Reasonable caption length
                return text
        
        return ""
    
    def extract_lists(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract lists from documentation."""
        lists = []
        
        for i, list_elem in enumerate(soup.find_all(['ul', 'ol'])):
            items = []
            for li in list_elem.find_all('li', recursive=False):
                items.append(clean_text(li.get_text()))
            
            if items:
                lists.append({
                    'id': f'list-{i}',
                    'type': list_elem.name,  # 'ul' or 'ol'
                    'items': items,
                    'parent_heading': self.get_parent_heading(list_elem)
                })
        
        return lists
    
    def get_parent_heading(self, element: BeautifulSoup) -> str:
        """Get the nearest parent heading for an element."""
        parent = element.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        return clean_text(parent.get_text()) if parent else ""
    
    def extract_topics(self, content: str) -> List[str]:
        """Extract potential topics from content."""
        topics = []
        
        # Look for common topic indicators
        patterns = [
            r'^(?:how to|guide to|tutorial on|understanding)\s+(.+)',
            r'^(?:introduction to|overview of|getting started with)\s+(.+)',
            r'^(?:working with|using|managing|configuring)\s+(.+)',
            r'^(?:best practices for|tips for|troubleshooting)\s+(.+)'
        ]
        
        sentences = content.split('. ')
        for sentence in sentences:
            for pattern in patterns:
                match = re.search(pattern, sentence.lower())
                if match and len(match.group(1)) > 5:
                    topic = match.group(1).strip().title()
                    if topic not in topics:
                        topics.append(topic)
        
        return topics[:10]  # Limit to top 10 topics
    
    def clean_documentation_content(self, content: str) -> str:
        """Clean documentation-specific content."""
        # Remove common documentation noise
        noise_patterns = [
            r'Last updated.*?\n',
            r'Version.*?\n',
            r'Copyright.*?\n',
            r'All rights reserved.*?\n',
            r'Page \d+ of \d+',
            r'Table of Contents',
            r'Navigation',
            r'Search.*?\n'
        ]
        
        cleaned = content
        for pattern in noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove excessive newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned.strip()
    
    def parse_multiple_pages(self, pages_data: Dict[str, Dict]) -> List[Dict]:
        """Parse multiple documentation pages."""
        parsed_pages = []
        
        for url, data in pages_data.items():
            try:
                parsed = self.parse_page(
                    url, 
                    data['html'], 
                    data['content']
                )
                parsed_pages.append(parsed)
            except Exception as e:
                logger.error(f"Error parsing {url}: {e}")
                continue
        
        return parsed_pages