import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from config import config


class OutputGenerator:
    """Generates structured output in various formats."""
    
    def __init__(self):
        self.timestamp = datetime.now().isoformat()
    
    def generate_json(self, modules: List[Dict], include_metadata: bool = False) -> str:
        """Generate JSON output in the specified format."""
        output = []
        
        for module in modules:
            module_output = {
                'module': module.get('module', ''),
                'Description': module.get('Description', ''),
                'Submodules': module.get('Submodules', {})
            }
            
            if include_metadata:
                module_output['metadata'] = {
                    'confidence_score': module.get('confidence_score', 0.5),
                    'source_urls': module.get('source_urls', []),
                    'extraction_timestamp': self.timestamp
                }
            
            output.append(module_output)
        
        # Format with proper indentation
        return json.dumps(output, indent=2, ensure_ascii=False)
    
    def generate_markdown(self, modules: List[Dict]) -> str:
        """Generate markdown output for easy reading."""
        md_lines = []
        md_lines.append(f"# Documentation Modules Analysis")
        md_lines.append(f"*Generated: {self.timestamp}*\n")
        
        for i, module in enumerate(modules, 1):
            md_lines.append(f"## {i}. {module.get('module', 'Unnamed Module')}")
            md_lines.append(f"**Description**: {module.get('Description', '')}\n")
            
            submodules = module.get('Submodules', {})
            if submodules:
                md_lines.append("### Submodules:")
                for submodule, description in submodules.items():
                    md_lines.append(f"- **{submodule}**: {description}")
            else:
                md_lines.append("*No submodules identified*")
            
            md_lines.append("")  # Empty line between modules
        
        return '\n'.join(md_lines)
    
    def generate_csv(self, modules: List[Dict]) -> str:
        """Generate CSV output for spreadsheet import."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'module', 'description', 'submodule', 
            'submodule_description', 'confidence_score'
        ])
        
        # Write data
        for module in modules:
            module_name = module.get('module', '')
            description = module.get('Description', '')
            confidence = module.get('confidence_score', 0.5)
            
            submodules = module.get('Submodules', {})
            if submodules:
                for submodule, sub_desc in submodules.items():
                    writer.writerow([
                        module_name, description, 
                        submodule, sub_desc, confidence
                    ])
            else:
                # Write module even if no submodules
                writer.writerow([module_name, description, '', '', confidence])
        
        return output.getvalue()
    
    def generate_html_report(self, modules: List[Dict]) -> str:
        """Generate HTML report for web display."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Documentation Modules Analysis</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; }}
                .module {{ background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px; }}
                .module h2 {{ color: #2c3e50; margin-top: 0; }}
                .submodule {{ margin: 10px 0; padding: 10px; background: white; border-left: 4px solid #3498db; }}
                .confidence {{ float: right; background: #3498db; color: white; padding: 5px 10px; border-radius: 4px; }}
                .timestamp {{ color: #7f8c8d; font-style: italic; }}
            </style>
        </head>
        <body>
            <h1>📚 Documentation Modules Analysis</h1>
            <p class="timestamp">Generated: {self.timestamp}</p>
        """
        
        for module in modules:
            confidence = module.get('confidence_score', 0.5)
            confidence_percent = int(confidence * 100)
            
            html += f"""
            <div class="module">
                <span class="confidence">{confidence_percent}% confident</span>
                <h2>{module.get('module', 'Unnamed Module')}</h2>
                <p><strong>Description:</strong> {module.get('Description', '')}</p>
            """
            
            submodules = module.get('Submodules', {})
            if submodules:
                html += "<h3>Submodules:</h3>"
                for submodule, description in submodules.items():
                    html += f"""
                    <div class="submodule">
                        <strong>{submodule}</strong>: {description}
                    </div>
                    """
            else:
                html += "<p><em>No submodules identified</em></p>"
            
            html += "</div>"
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return html
    
    def generate_summary_stats(self, modules: List[Dict]) -> Dict[str, Any]:
        """Generate summary statistics about the extraction."""
        total_modules = len(modules)
        total_submodules = sum(len(m.get('Submodules', {})) for m in modules)
        
        # Calculate average confidence
        confidences = [m.get('confidence_score', 0.5) for m in modules]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Find modules with highest confidence
        top_modules = sorted(
            modules, 
            key=lambda x: x.get('confidence_score', 0), 
            reverse=True
        )[:3]
        
        return {
            'total_modules': total_modules,
            'total_submodules': total_submodules,
            'average_confidence': round(avg_confidence, 3),
            'top_modules': [
                {'module': m['module'], 'confidence': m.get('confidence_score', 0)}
                for m in top_modules
            ],
            'extraction_timestamp': self.timestamp,
            'processing_time': datetime.now().isoformat()
        }