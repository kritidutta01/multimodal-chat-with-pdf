import streamlit as st
import PyPDF2
import openai
from io import BytesIO
import time
import re
from typing import List, Dict, Any, Tuple
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
import json
import hashlib
import warnings
warnings.filterwarnings('ignore')

# Page Configuration
st.set_page_config(
    page_title="🇮🇳 Indian Financial PDF Chat - Phase 2",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Indian Financial Theme
st.markdown("""
<style>
.main-header {
    text-align: center;
    padding: 1.5rem 0;
    background: linear-gradient(135deg, #ff9933 0%, #ffffff 50%, #138808 100%);
    color: #000080;
    border-radius: 15px;
    margin-bottom: 2rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.metric-card {
    background: #f8f9fa;
    padding: 1.2rem;
    border-radius: 10px;
    border-left: 5px solid #ff9933;
    margin: 0.8rem 0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.indian-metric {
    background: linear-gradient(45deg, #ff9933, #138808);
    color: white;
    padding: 1rem;
    border-radius: 8px;
    margin: 0.5rem 0;
    text-align: center;
    font-weight: bold;
}

.ai-response {
    background: #e8f5e8;
    padding: 1.2rem;
    border-radius: 10px;
    border-left: 5px solid #138808;
    margin: 1rem 0;
}

.user-message {
    background: #fff3e0;
    padding: 1.2rem;
    border-radius: 10px;
    border-left: 5px solid #ff9933;
    margin: 1rem 0;
}

.financial-dashboard {
    background: #f0f8ff;
    padding: 1.5rem;
    border-radius: 12px;
    border: 2px solid #138808;
    margin: 1rem 0;
}

.ratio-analysis {
    background: #fff9c4;
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #ffc107;
    margin: 0.5rem 0;
}

.risk-alert {
    background: #ffebee;
    color: #c62828;
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #f44336;
    margin: 1rem 0;
}

.success-box {
    background: #e8f5e8;
    color: #2e7d32;
    padding: 1.2rem;
    border-radius: 10px;
    border: 2px solid #4caf50;
    margin: 1rem 0;
}

.indian-company-header {
    background: linear-gradient(90deg, #ff9933, #138808);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    text-align: center;
    margin: 1rem 0;
}

.nse-ticker {
    background: #000080;
    color: white;
    padding: 0.3rem 0.8rem;
    border-radius: 15px;
    font-weight: bold;
    display: inline-block;
    margin: 0.2rem;
}

.bse-ticker {
    background: #dc3545;
    color: white;
    padding: 0.3rem 0.8rem;
    border-radius: 15px;
    font-weight: bold;
    display: inline-block;
    margin: 0.2rem;
}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# INDIAN FINANCIAL DATA PATTERNS AND CONFIGURATIONS
# ============================================================================

class IndianFinancialExtractor:
    """Specialized extractor for Indian financial documents"""
    
    def __init__(self):
        self.indian_currency_patterns = [
            r'₹\s*([\d,]+\.?\d*)\s*crores?',
            r'rs\.?\s*([\d,]+\.?\d*)\s*crores?',
            r'inr\s*([\d,]+\.?\d*)\s*crores?',
            r'([\d,]+\.?\d*)\s*crores?',
            r'₹\s*([\d,]+\.?\d*)\s*lakhs?',
            r'([\d,]+\.?\d*)\s*lakhs?'
        ]
        
        self.indian_financial_metrics = {
            'revenue': [
                r'total income\s*.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'revenue from operations\s*.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'net sales\s*.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'total revenue\s*.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'turnover\s*.*?₹?\s*([\d,]+\.?\d*)\s*crores?'
            ],
            'net_profit': [
                r'net profit.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'profit after tax.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'pat\s*.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'net income.*?₹?\s*([\d,]+\.?\d*)\s*crores?'
            ],
            'ebitda': [
                r'ebitda.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'earnings before.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'operating profit.*?₹?\s*([\d,]+\.?\d*)\s*crores?'
            ],
            'total_assets': [
                r'total assets.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'total resources.*?₹?\s*([\d,]+\.?\d*)\s*crores?'
            ],
            'total_debt': [
                r'total debt.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'total borrowings.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'debt.*?₹?\s*([\d,]+\.?\d*)\s*crores?'
            ],
            'cash': [
                r'cash and cash equivalents.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'cash and bank.*?₹?\s*([\d,]+\.?\d*)\s*crores?',
                r'liquid assets.*?₹?\s*([\d,]+\.?\d*)\s*crores?'
            ],
            'eps': [
                r'earnings per share.*?₹?\s*([\d,]+\.?\d*)',
                r'eps.*?₹?\s*([\d,]+\.?\d*)',
                r'basic eps.*?₹?\s*([\d,]+\.?\d*)'
            ],
            'book_value': [
                r'book value per share.*?₹?\s*([\d,]+\.?\d*)',
                r'nav per share.*?₹?\s*([\d,]+\.?\d*)'
            ]
        }
        
        self.indian_ratios = {
            'pe_ratio': r'p/e ratio.*?([\d,]+\.?\d*)',
            'pb_ratio': r'p/b ratio.*?([\d,]+\.?\d*)',
            'roe': r'return on equity.*?([\d,]+\.?\d*)%?',
            'roa': r'return on assets.*?([\d,]+\.?\d*)%?',
            'debt_equity': r'debt.*?equity.*?ratio.*?([\d,]+\.?\d*)',
            'current_ratio': r'current ratio.*?([\d,]+\.?\d*)'
        }

        self.indian_sectors = {
            'BANKING': ['bank', 'financial services', 'nbfc'],
            'IT': ['information technology', 'software', 'tech services'],
            'PHARMA': ['pharmaceutical', 'healthcare', 'drugs'],
            'AUTO': ['automobile', 'automotive', 'vehicle'],
            'STEEL': ['steel', 'metal', 'iron'],
            'OIL_GAS': ['oil', 'gas', 'petroleum', 'refinery'],
            'TELECOM': ['telecom', 'communication', 'mobile'],
            'FMCG': ['consumer goods', 'fmcg', 'personal care'],
            'CEMENT': ['cement', 'building materials'],
            'POWER': ['power', 'electricity', 'energy']
        }

    def extract_indian_metrics(self, text: str) -> Dict:
        """Extract financial metrics specific to Indian companies"""
        metrics = {}
        text_lower = text.lower()
        
        for metric, patterns in self.indian_financial_metrics.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE | re.DOTALL)
                if matches:
                    try:
                        # Handle different formats
                        value_str = matches[0].replace(',', '')
                        if 'crore' in pattern:
                            value = float(value_str)  # Already in crores
                        elif 'lakh' in pattern:
                            value = float(value_str) / 10  # Convert lakhs to crores
                        else:
                            value = float(value_str)
                        
                        metrics[metric] = value
                        break
                    except (ValueError, IndexError):
                        continue
        
        return metrics

    def identify_indian_company(self, text: str) -> Dict:
        """Identify Indian company details"""
        company_info = {
            'name': None,
            'sector': None,
            'nse_symbol': None,
            'bse_code': None
        }
        
        # Extract company name (usually in header or title)
        name_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Limited',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Ltd',
            r'([A-Z]{2,}\s*[A-Z]*)\s+LIMITED'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text[:1000])
            if match:
                company_info['name'] = match.group(1)
                break
        
        # Identify sector
        for sector, keywords in self.indian_sectors.items():
            for keyword in keywords:
                if keyword in text.lower():
                    company_info['sector'] = sector
                    break
            if company_info['sector']:
                break
        
        # Extract stock symbols
        nse_match = re.search(r'NSE[:\s]*([A-Z]+)', text.upper())
        if nse_match:
            company_info['nse_symbol'] = nse_match.group(1)
        
        bse_match = re.search(r'BSE[:\s]*(\d+)', text)
        if bse_match:
            company_info['bse_code'] = bse_match.group(1)
        
        return company_info

    def convert_to_crores(self, amount: float, unit: str) -> float:
        """Convert amounts to crores"""
        unit = unit.lower()
        if 'lakh' in unit:
            return amount / 10
        elif 'thousand' in unit:
            return amount / 1000
        elif 'crore' in unit:
            return amount
        else:
            return amount  # Assume already in crores

# ============================================================================
# INDIAN MARKET DATA AND BENCHMARKS
# ============================================================================

INDIAN_SECTOR_BENCHMARKS = {
    'BANKING': {
        'pe_ratio': 12.5,
        'pb_ratio': 1.8,
        'roe': 15.0,
        'roa': 1.2,
        'nim': 3.5,  # Net Interest Margin
        'casa_ratio': 45.0  # Current Account Savings Account
    },
    'IT': {
        'pe_ratio': 28.0,
        'pb_ratio': 4.5,
        'roe': 25.0,
        'roa': 18.0,
        'operating_margin': 22.0,
        'dollar_revenue': 75.0  # % revenue from exports
    },
    'PHARMA': {
        'pe_ratio': 24.0,
        'pb_ratio': 3.2,
        'roe': 18.0,
        'roa': 12.0,
        'rd_expense': 8.0,  # R&D as % of revenue
        'export_revenue': 60.0
    },
    'AUTO': {
        'pe_ratio': 18.0,
        'pb_ratio': 2.1,
        'roe': 14.0,
        'roa': 8.0,
        'asset_turnover': 1.8,
        'working_capital': 15.0
    },
    'FMCG': {
        'pe_ratio': 32.0,
        'pb_ratio': 5.2,
        'roe': 22.0,
        'roa': 15.0,
        'gross_margin': 45.0,
        'ad_spend': 12.0  # Advertising spend %
    }
}

INDIAN_FINANCIAL_TEMPLATES = {
    "Annual Report Analysis": [
        "What is the company's revenue growth over the past 3 years?",
        "How has the profit margin changed?",
        "What are the key business segments and their performance?",
        "What are the major risks highlighted by management?",
        "What is the company's expansion strategy?"
    ],
    
    "Quarterly Results Review": [
        "What are the quarterly revenue and profit figures?",
        "How do these compare to the same quarter last year?",
        "What factors drove the performance this quarter?",
        "What is the management guidance for the next quarter?",
        "Are there any one-time items affecting results?"
    ],
    
    "Banking Sector Analysis": [
        "What is the Net Interest Margin (NIM)?",
        "What are the gross and net NPA levels?",
        "What is the CASA ratio?",
        "How is the credit growth performing?",
        "What is the provision coverage ratio?"
    ],
    
    "IT Sector Deep Dive": [
        "What percentage of revenue comes from exports?",
        "What are the key client additions this quarter?",
        "How is the company positioned in emerging technologies?",
        "What is the employee utilization rate?",
        "What are the currency hedging strategies?"
    ],
    
    "Auto Sector Review": [
        "What are the volume growth numbers by segment?",
        "How is the company managing raw material cost inflation?",
        "What are the capacity utilization levels?",
        "What is the progress on electric vehicle strategy?",
        "How is the rural vs urban demand trend?"
    ],
    
    "Pharma Sector Analysis": [
        "What is the R&D expenditure as percentage of sales?",
        "How are the regulatory approvals progressing?",
        "What is the domestic vs export revenue split?",
        "What are the new product launches this year?",
        "How is the company managing pricing pressures?"
    ]
}

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize session state for Indian financial analysis"""
    if 'pdf_processed' not in st.session_state:
        st.session_state.pdf_processed = False
    if 'pdf_text' not in st.session_state:
        st.session_state.pdf_text = ""
    if 'pdf_pages' not in st.session_state:
        st.session_state.pdf_pages = []
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'financial_metrics' not in st.session_state:
        st.session_state.financial_metrics = {}
    if 'company_info' not in st.session_state:
        st.session_state.company_info = {}
    if 'metrics' not in st.session_state:
        st.session_state.metrics = {
            'processing_time': 0,
            'total_queries': 0,
            'successful_queries': 0,
            'avg_response_time': 0,
            'response_times': [],
            'start_time': time.time()
        }
    if 'vectorizer' not in st.session_state:
        st.session_state.vectorizer = None
    if 'doc_vectors' not in st.session_state:
        st.session_state.doc_vectors = None
    if 'api_configured' not in st.session_state:
        st.session_state.api_configured = False
    if 'extractor' not in st.session_state:
        st.session_state.extractor = IndianFinancialExtractor()

# ============================================================================
# AI CONFIGURATION WITH INDIAN CONTEXT
# ============================================================================

def configure_ai():
    """Configure AI with Indian financial context"""
    with st.sidebar:
        st.markdown("### 🤖 AI Configuration")
        
        api_provider = st.selectbox(
            "Choose AI Provider",
            ["OpenAI (Recommended)", "Offline Mode (Indian NLP)", "Hugging Face"],
            key="api_provider"
        )
        
        if api_provider == "OpenAI (Recommended)":
            api_key = st.text_input(
                "OpenAI API Key",
                type="password",
                help="Get your API key from https://platform.openai.com/api-keys"
            )
            model = st.selectbox(
                "Model",
                ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
                key="openai_model"
            )
            
            if api_key:
                openai.api_key = api_key
                st.session_state.api_configured = True
                st.success("✅ OpenAI configured for Indian markets!")
            
        elif api_provider == "Hugging Face":
            hf_token = st.text_input(
                "Hugging Face Token",
                type="password",
                help="Get your token from https://huggingface.co/settings/tokens"
            )
            if hf_token:
                st.session_state.hf_token = hf_token
                st.session_state.api_configured = True
                st.success("✅ Hugging Face configured!")
        
        else:  # Offline Mode
            st.info("🧠 Advanced Indian Financial NLP Active")
            st.session_state.api_configured = True
        
        return api_provider

# ============================================================================
# ENHANCED PDF PROCESSING FOR INDIAN DOCUMENTS
# ============================================================================

def extract_text_from_pdf(pdf_file):
    """Extract text with Indian document patterns"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        text_pages = []
        full_text = ""
        
        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            # Clean Indian financial document text
            cleaned_text = clean_indian_financial_text(page_text)
            text_pages.append({
                'page_num': i + 1,
                'text': cleaned_text
            })
            full_text += f"[Page {i + 1}] {cleaned_text}\n"
        
        return full_text, text_pages, len(pdf_reader.pages)
    
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None, None, 0

def clean_indian_financial_text(text: str) -> str:
    """Clean and normalize Indian financial document text"""
    # Replace common Indian financial document artifacts
    text = re.sub(r'₹\s*', '₹', text)
    text = re.sub(r'\s+crores?', ' crores', text)
    text = re.sub(r'\s+lakhs?', ' lakhs', text)
    text = re.sub(r'Rs\.?\s*', '₹', text)
    text = re.sub(r'INR\s*', '₹', text)
    
    # Normalize spacing
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

# ============================================================================
# INDIAN FINANCIAL ANALYSIS FUNCTIONS
# ============================================================================

def analyze_indian_financial_document(text: str) -> Tuple[Dict, Dict]:
    """Comprehensive analysis of Indian financial document"""
    
    extractor = st.session_state.extractor
    
    # Extract financial metrics
    financial_metrics = extractor.extract_indian_metrics(text)
    
    # Identify company information
    company_info = extractor.identify_indian_company(text)
    
    # Calculate additional ratios if possible
    if financial_metrics.get('revenue') and financial_metrics.get('net_profit'):
        net_margin = (financial_metrics['net_profit'] / financial_metrics['revenue']) * 100
        financial_metrics['net_margin'] = round(net_margin, 2)
    
    if financial_metrics.get('total_debt') and financial_metrics.get('revenue'):
        debt_to_revenue = financial_metrics['total_debt'] / financial_metrics['revenue']
        financial_metrics['debt_to_revenue'] = round(debt_to_revenue, 2)
    
    return financial_metrics, company_info

def create_indian_financial_dashboard(metrics: Dict, company_info: Dict):
    """Create Indian company financial dashboard"""
    
    company_name = company_info.get('name', 'Indian Company')
    sector = company_info.get('sector', 'Unknown Sector')
    
    # Company Header
    st.markdown(f"""
    <div class="indian-company-header">
        <h2>🏢 {company_name}</h2>
        <p>Sector: {sector}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stock Exchange Info
    col1, col2, col3 = st.columns(3)
    with col1:
        if company_info.get('nse_symbol'):
            st.markdown(f'<span class="nse-ticker">NSE: {company_info["nse_symbol"]}</span>', unsafe_allow_html=True)
    with col2:
        if company_info.get('bse_code'):
            st.markdown(f'<span class="bse-ticker">BSE: {company_info["bse_code"]}</span>', unsafe_allow_html=True)
    
    # Key Financial Metrics
    st.markdown("### 📊 Key Financial Metrics (₹ Crores)")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        revenue = metrics.get('revenue', 0)
        st.markdown(f"""
        <div class="indian-metric">
            💰 Revenue<br>
            ₹{revenue:,.0f} Cr
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        net_profit = metrics.get('net_profit', 0)
        st.markdown(f"""
        <div class="indian-metric">
            📈 Net Profit<br>
            ₹{net_profit:,.0f} Cr
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        eps = metrics.get('eps', 0)
        st.markdown(f"""
        <div class="indian-metric">
            💵 EPS<br>
            ₹{eps:.2f}
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        net_margin = metrics.get('net_margin', 0)
        st.markdown(f"""
        <div class="indian-metric">
            📊 Net Margin<br>
            {net_margin:.1f}%
        </div>
        """, unsafe_allow_html=True)

def create_sector_comparison(company_metrics: Dict, sector: str):
    """Compare against Indian sector benchmarks"""
    
    if sector not in INDIAN_SECTOR_BENCHMARKS:
        st.warning(f"Sector benchmarks not available for {sector}")
        return
    
    st.markdown(f"### 🏢 {sector} Sector Comparison")
    
    benchmarks = INDIAN_SECTOR_BENCHMARKS[sector]
    
    comparison_data = []
    
    # Compare available metrics
    for metric, benchmark in benchmarks.items():
        company_value = company_metrics.get(metric, 0)
        if company_value > 0:
            performance = "Above Average" if company_value > benchmark else "Below Average"
            comparison_data.append({
                'Metric': metric.replace('_', ' ').title(),
                'Company': f"{company_value:.1f}",
                'Sector Average': f"{benchmark:.1f}",
                'Performance': performance
            })
    
    if comparison_data:
        df = pd.DataFrame(comparison_data)
        
        # Color code the performance
        def color_performance(val):
            color = '#d4edda' if val == 'Above Average' else '#f8d7da'
            return f'background-color: {color}'
        
        styled_df = df.style.applymap(color_performance, subset=['Performance'])
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("Not enough data for sector comparison")

# ============================================================================
# ENHANCED AI RESPONSES FOR INDIAN MARKETS
# ============================================================================

def get_indian_financial_context_prompt(question: str, context: str, company_info: Dict, metrics: Dict) -> str:
    """Create enhanced prompt for Indian financial analysis"""
    
    sector = company_info.get('sector', 'Unknown')
    company_name = company_info.get('name', 'Company')
    
    system_prompt = f"""You are a senior equity research analyst specializing in Indian financial markets with 15+ years of experience analyzing Indian companies.

Company Context:
- Company: {company_name}
- Sector: {sector}
- NSE Symbol: {company_info.get('nse_symbol', 'N/A')}
- BSE Code: {company_info.get('bse_code', 'N/A')}

Key Financial Metrics (₹ Crores):
- Revenue: ₹{metrics.get('revenue', 0):,.0f} Cr
- Net Profit: ₹{metrics.get('net_profit', 0):,.0f} Cr
- EPS: ₹{metrics.get('eps', 0):.2f}
- Net Margin: {metrics.get('net_margin', 0):.1f}%

Document Context:
{context}

When analyzing this Indian company:
1. Use Indian financial terminology (Crores, Lakhs, PAT, EBITDA)
2. Consider Indian regulatory environment (SEBI, RBI guidelines)
3. Reference sector-specific metrics relevant to Indian markets
4. Consider macroeconomic factors affecting Indian businesses
5. Use INR currency format and Indian accounting standards
6. Provide insights relevant to Indian investors
7. Always cite specific page numbers and figures from the document

Your analysis should be professional, detailed, and suitable for Indian equity research reports."""

    return system_prompt

def generate_indian_ai_response(question: str, context: str) -> str:
    """Generate AI response optimized for Indian financial analysis"""
    
    company_info = st.session_state.company_info
    metrics = st.session_state.financial_metrics
    
    api_provider = st.session_state.get('api_provider', 'Offline Mode (Indian NLP)')
    
    if "OpenAI" in api_provider and st.session_state.api_configured:
        try:
            system_prompt = get_indian_financial_context_prompt(question, context, company_info, metrics)
            
            response = openai.ChatCompletion.create(
                model=st.session_state.get('openai_model', 'gpt-3.5-turbo'),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                max_tokens=600,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            st.error(f"OpenAI API Error: {str(e)}")
            return generate_indian_offline_response(question, context)
    
    else:
        return generate_indian_offline_response(question, context)

def generate_indian_offline_response(question: str, context: str) -> str:
    """Generate sophisticated offline response for Indian financial queries"""
    
    question_lower = question.lower()
    company_info = st.session_state.company_info
    metrics = st.session_state.financial_metrics
    company_name = company_info.get('name', 'the company')
    sector = company_info.get('sector', 'the sector')
    
    # Sector-specific responses
    if 'revenue' in question_lower or 'sales' in question_lower or 'turnover' in question_lower:
        revenue = metrics.get('revenue', 0)
        net_margin = metrics.get('net_margin', 0)
        
        response = f"📊 **Revenue Analysis for {company_name}:**\n\n"
        if revenue > 0:
            response += f"• **Total Revenue:** ₹{revenue:,.0f} crores\n"
            if net_margin > 0:
                response += f"• **Net Profit Margin:** {net_margin:.1f}%\n"
            
            # Sector context
            if sector in INDIAN_SECTOR_BENCHMARKS:
                sector_avg = INDIAN_SECTOR_BENCHMARKS[sector].get('operating_margin', 0)
                if sector_avg > 0:
                    response += f"• **Sector Average Margin:** {sector_avg:.1f}%\n"
            
            response += f"\n**Analysis:** "
            if net_margin > 15:
                response += "Strong profitability indicating efficient operations and pricing power."
            elif net_margin > 8:
                response += "Healthy margins but room for improvement in cost management."
            else:
                response += "Low margins suggest pressure on costs or competitive pricing."
        else:
            response += "Revenue data not clearly identified in the document. Please check for alternative terminology like 'Total Income' or 'Net Sales'."
        
        return response + "\n\n*Analysis based on Indian financial document patterns*"
    
    elif 'profit' in question_lower or 'pat' in question_lower or 'net income' in question_lower:
        net_profit = metrics.get('net_profit', 0)
        revenue = metrics.get('revenue', 0)
        
        response = f"💰 **Profitability Analysis for {company_name}:**\n\n"
        if net_profit > 0:
            response += f"• **Net Profit (PAT):** ₹{net_profit:,.0f} crores\n"
            if revenue > 0:
                margin = (net_profit / revenue) * 100
                response += f"• **Net Profit Margin:** {margin:.2f}%\n"
            
            response += f"\n**Profitability Assessment:** "
            if net_profit > 1000:
                response += "Strong absolute profit numbers indicating solid business performance."
            elif net_profit > 100:
                response += "Healthy profit levels showing sustainable operations."
            elif net_profit > 0:
                response += "Positive profitability but relatively modest scale."
            else:
                response += "Profitability concerns that need management attention."
        
        return response + "\n\n*Based on Indian accounting standards analysis*"
    
    elif 'debt' in question_lower or 'leverage' in question_lower or 'borrowing' in question_lower:
        total_debt = metrics.get('total_debt', 0)
        revenue = metrics.get('revenue', 0)
        debt_to_revenue = metrics.get('debt_to_revenue', 0)
        
        response = f"⚖️ **Debt Analysis for {company_name}:**\n\n"
        if total_debt > 0:
            response += f"• **Total Debt:** ₹{total_debt:,.0f} crores\n"
            if debt_to_revenue > 0:
                response += f"• **Debt-to-Revenue Ratio:** {debt_to_revenue:.2f}x\n"
            
            response += f"\n**Leverage Assessment:** "
            if debt_to_revenue > 2:
                response += "⚠️ High leverage levels may indicate financial stress or aggressive growth strategy."
            elif debt_to_revenue > 1:
                response += "Moderate debt levels - manageable but requires monitoring."
            elif debt_to_revenue > 0.5:
                response += "Conservative debt levels indicating prudent financial management."
            else:
                response += "Low debt levels providing financial flexibility."
        
        return response + "\n\n*Debt analysis based on Indian corporate finance patterns*"
    
    elif 'sector' in question_lower or 'industry' in question_lower or 'peer' in question_lower:
        response = f"🏢 **Sector Analysis - {sector}:**\n\n"
        
        if sector in INDIAN_SECTOR_BENCHMARKS:
            benchmarks = INDIAN_SECTOR_BENCHMARKS[sector]
            response += f"**Key {sector} Sector Metrics:**\n"
            for metric, value in benchmarks.items():
                metric_name = metric.replace('_', ' ').title()
                if 'ratio' in metric or 'margin' in metric:
                    response += f"• {metric_name}: {value:.1f}%\n"
                else:
                    response += f"• {metric_name}: {value:.1f}\n"
            
            # Sector-specific insights
            if sector == 'BANKING':
                response += f"\n**Banking Sector Focus Areas:**\n• Asset quality (NPA levels)\n• Net Interest Margins\n• CASA ratio for funding cost management\n• Capital adequacy ratios"
            elif sector == 'IT':
                response += f"\n**IT Sector Key Drivers:**\n• Dollar revenue growth\n• Client mining and new acquisitions\n• Digital transformation capabilities\n• Employee utilization rates"
            elif sector == 'PHARMA':
                response += f"\n**Pharma Sector Considerations:**\n• R&D investment for future growth\n• Regulatory approvals pipeline\n• Domestic vs export market dynamics\n• Generic vs branded product mix"
        
        return response + "\n\n*Analysis based on Indian sector dynamics*"
    
    elif 'summary' in question_lower or 'overview' in question_lower:
        response = f"📋 **Executive Summary - {company_name}:**\n\n"
        
        response += f"**Company Profile:**\n"
        response += f"• Sector: {sector}\n"
        if company_info.get('nse_symbol'):
            response += f"• NSE Symbol: {company_info['nse_symbol']}\n"
        
        response += f"\n**Financial Snapshot (₹ Crores):**\n"
        for metric, value in metrics.items():
            if value > 0:
                metric_name = metric.replace('_', ' ').title()
                if 'margin' in metric or 'ratio' in metric:
                    response += f"• {metric_name}: {value:.2f}%\n"
                elif metric == 'eps':
                    response += f"• {metric_name}: ₹{value:.2f}\n"
                else:
                    response += f"• {metric_name}: ₹{value:,.0f} Cr\n"
        
        response += f"\n**Investment Considerations:**\n"
        net_margin = metrics.get('net_margin', 0)
        debt_to_revenue = metrics.get('debt_to_revenue', 0)
        
        if net_margin > 15:
            response += "• ✅ Strong profitability metrics\n"
        elif net_margin > 5:
            response += "• ⚠️ Moderate profitability - monitor trends\n"
        
        if debt_to_revenue < 0.5:
            response += "• ✅ Conservative debt levels\n"
        elif debt_to_revenue < 1:
            response += "• ⚠️ Moderate leverage\n"
        else:
            response += "• 🚨 High debt levels require attention\n"
        
        return response + "\n\n*Comprehensive analysis using Indian market frameworks*"
    
    else:
        # General contextual response
        relevant_sentences = context.split('.')[:3]
        response = f"💡 **Analysis for {company_name}:**\n\n"
        response += f"Based on the document content:\n\n"
        for i, sentence in enumerate(relevant_sentences, 1):
            if sentence.strip():
                response += f"{i}. {sentence.strip()}.\n"
        
        # Add financial context if available
        if metrics:
            response += f"\n**Key Metrics Context:**\n"
            revenue = metrics.get('revenue', 0)
            net_profit = metrics.get('net_profit', 0)
            if revenue > 0 and net_profit > 0:
                margin = (net_profit / revenue) * 100
                response += f"• Current net margin: {margin:.1f}%\n"
        
        return response + "\n\n*For specific insights, please ask targeted questions about revenue, profitability, debt, or sector performance.*"

# ============================================================================
# INDIAN FINANCIAL TEMPLATES AND QUICK ANALYSIS
# ============================================================================

def create_indian_analysis_templates():
    """Create analysis templates specific to Indian financial documents"""
    
    st.markdown("### 🎯 Quick Analysis Templates for Indian Markets")
    
    template_choice = st.selectbox(
        "Choose analysis type:",
        list(INDIAN_FINANCIAL_TEMPLATES.keys()),
        key="indian_template_selector"
    )
    
    if template_choice:
        st.markdown(f"**{template_choice} Questions:**")
        
        questions = INDIAN_FINANCIAL_TEMPLATES[template_choice]
        
        cols = st.columns(2)
        for i, question in enumerate(questions):
            col_idx = i % 2
            with cols[col_idx]:
                if st.button(f"❓ {question}", key=f"indian_template_{template_choice}_{i}", use_container_width=True):
                    return question
    
    return None

# ============================================================================
# SEMANTIC SEARCH WITH INDIAN FINANCIAL CONTEXT
# ============================================================================

def create_indian_document_vectors(text_pages):
    """Create vectors optimized for Indian financial documents"""
    try:
        documents = [page['text'] for page in text_pages]
        
        # Custom stop words for Indian financial documents
        indian_stop_words = [
            'crore', 'crores', 'lakh', 'lakhs', 'rupees', 'inr', 'rs',
            'limited', 'ltd', 'company', 'annual', 'report', 'financial',
            'year', 'ended', 'march', 'quarter', 'page', 'note', 'schedule'
        ]
        
        vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 3),  # Include trigrams for financial phrases
            min_df=1,
            max_df=0.95
        )
        
        # Add Indian financial stop words
        if hasattr(vectorizer, 'stop_words'):
            vectorizer.stop_words = list(vectorizer.stop_words) + indian_stop_words
        
        doc_vectors = vectorizer.fit_transform(documents)
        return vectorizer, doc_vectors
        
    except Exception as e:
        st.error(f"Error creating document vectors: {str(e)}")
        return None, None

def semantic_search_indian(query: str, top_k: int = 3) -> List[Dict]:
    """Semantic search optimized for Indian financial queries"""
    if not st.session_state.vectorizer or st.session_state.doc_vectors is None:
        return []
    
    try:
        # Enhance query with Indian financial terms
        enhanced_query = enhance_indian_query(query)
        
        query_vector = st.session_state.vectorizer.transform([enhanced_query])
        similarities = cosine_similarity(query_vector, st.session_state.doc_vectors).flatten()
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.05:  # Lower threshold for Indian docs
                results.append({
                    'page_num': st.session_state.pdf_pages[idx]['page_num'],
                    'text': st.session_state.pdf_pages[idx]['text'][:600] + "...",
                    'similarity': similarities[idx]
                })
        
        return results
        
    except Exception as e:
        st.error(f"Error in semantic search: {str(e)}")
        return []

def enhance_indian_query(query: str) -> str:
    """Enhance query with Indian financial synonyms"""
    enhancements = {
        'revenue': 'revenue sales turnover total income net sales',
        'profit': 'profit pat net income earnings',
        'debt': 'debt borrowings loan liability',
        'cash': 'cash bank balance liquid assets',
        'margin': 'margin profitability efficiency',
        'growth': 'growth increase expansion development'
    }
    
    enhanced_query = query.lower()
    for key, synonyms in enhancements.items():
        if key in enhanced_query:
            enhanced_query += f" {synonyms}"
    
    return enhanced_query

# ============================================================================
# MAIN APPLICATION LOGIC
# ============================================================================

def process_indian_pdf(uploaded_file):
    """Process PDF with Indian financial document analysis"""
    with st.spinner("🔄 Processing Indian financial document..."):
        start_time = time.time()
        
        # Extract text
        pdf_text, pdf_pages, num_pages = extract_text_from_pdf(uploaded_file)
        
        if pdf_text:
            # Analyze for Indian financial metrics
            financial_metrics, company_info = analyze_indian_financial_document(pdf_text)
            
            # Create vectors for semantic search
            vectorizer, doc_vectors = create_indian_document_vectors(pdf_pages)
            
            # Update session state
            st.session_state.pdf_text = pdf_text
            st.session_state.pdf_pages = pdf_pages
            st.session_state.financial_metrics = financial_metrics
            st.session_state.company_info = company_info
            st.session_state.vectorizer = vectorizer
            st.session_state.doc_vectors = doc_vectors
            st.session_state.pdf_processed = True
            st.session_state.current_file = uploaded_file.name
            
            # Update metrics
            processing_time = time.time() - start_time
            update_metrics(processing_time=processing_time)
            
            return processing_time, num_pages, financial_metrics, company_info
    
    return None, None, None, None

def update_metrics(processing_time: float = None, response_time: float = None, success: bool = True):
    """Update performance metrics"""
    if processing_time is not None:
        st.session_state.metrics['processing_time'] = processing_time
    
    if response_time is not None:
        st.session_state.metrics['response_times'].append(response_time)
        st.session_state.metrics['avg_response_time'] = np.mean(st.session_state.metrics['response_times'])
        st.session_state.metrics['total_queries'] += 1
        
        if success:
            st.session_state.metrics['successful_queries'] += 1

def display_indian_metrics():
    """Display enhanced metrics for Indian financial analysis"""
    metrics = st.session_state.metrics
    
    st.markdown("### 📊 Performance Analytics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "⚡ Processing",
            f"{metrics['processing_time']:.1f}s" if metrics['processing_time'] > 0 else "-- s",
            delta="Target: <30s",
            help="PDF processing and financial extraction time"
        )
    
    with col2:
        st.metric(
            "🤖 AI Response",
            f"{metrics['avg_response_time']:.1f}s" if metrics['avg_response_time'] > 0 else "-- s",
            delta="Target: <5s",
            help="Average AI response generation time"
        )
    
    with col3:
        st.metric(
            "❓ Total Queries",
            metrics['total_queries'],
            help="Number of financial analysis queries"
        )
    
    with col4:
        success_rate = (metrics['successful_queries'] / metrics['total_queries'] * 100) if metrics['total_queries'] > 0 else 0
        st.metric(
            "✅ Success Rate",
            f"{success_rate:.0f}%",
            delta="Target: >85%",
            help="Percentage of successful financial analyses"
        )

def main():
    """Main application with Indian financial focus"""
    
    # Initialize session state FIRST
    init_session_state()
    
    # Header with Indian theme
    st.markdown("""
    <div class="main-header">
        <h1>🇮🇳 Indian Financial PDF Chat - Phase 2</h1>
        <p>Advanced AI analysis for Indian equity research and financial documents</p>
        <p><strong>Specialized for:</strong> Annual Reports | Quarterly Results | Investor Presentations | Research Reports</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Configure AI
    api_provider = configure_ai()
    
    # Main layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📁 Document Upload")
        
        # File upload with Indian context
        uploaded_file = st.file_uploader(
            "Upload Indian Financial Document",
            type="pdf",
            help="Upload annual reports, quarterly results, investor presentations, or research reports of Indian companies"
        )
        
        if uploaded_file is not None:
            if not st.session_state.pdf_processed or st.session_state.get('current_file') != uploaded_file.name:
                processing_time, num_pages, financial_metrics, company_info = process_indian_pdf(uploaded_file)
                
                if processing_time:
                    st.markdown(f"""
                    <div class="success-box">
                        ✅ <strong>Document Processed Successfully!</strong><br>
                        📄 Pages: {num_pages}<br>
                        ⏱️ Processing Time: {processing_time:.1f}s<br>
                        🏢 Company: {company_info.get('name', 'Identified')}<br>
                        🏭 Sector: {company_info.get('sector', 'Classified')}<br>
                        💰 Metrics Extracted: {len(financial_metrics)}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Display financial dashboard
            if st.session_state.pdf_processed:
                create_indian_financial_dashboard(
                    st.session_state.financial_metrics,
                    st.session_state.company_info
                )
                
                # Sector comparison
                sector = st.session_state.company_info.get('sector')
                if sector and sector in INDIAN_SECTOR_BENCHMARKS:
                    create_sector_comparison(st.session_state.financial_metrics, sector)
        
        # Analysis templates
        if st.session_state.pdf_processed:
            template_question = create_indian_analysis_templates()
            if template_question:
                # Add to chat history
                st.session_state.chat_history.append({"role": "user", "content": template_question})
                
                # Generate response
                start_time = time.time()
                search_results = semantic_search_indian(template_question, top_k=3)
                
                if search_results:
                    context = "\n\n".join([f"[Page {result['page_num']}] {result['text']}" for result in search_results])
                else:
                    context = st.session_state.pdf_text[:1000]
                
                response = generate_indian_ai_response(template_question, context)
                response_time = time.time() - start_time
                
                # Update metrics and add response
                update_metrics(response_time=response_time, success=True)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
    
    with col2:
        st.markdown("### 💬 Financial Analysis Chat")
        
        # Display performance metrics
        display_indian_metrics()
        
        # Chat interface
        if st.session_state.pdf_processed:
            
            # Chat history display
            chat_container = st.container()
            with chat_container:
                for message in st.session_state.chat_history:
                    if message["role"] == "user":
                        st.markdown(f"""
                        <div class="user-message">
                            <strong>👤 Analyst Query:</strong><br>
                            {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="ai-response">
                            <strong>🤖 AI Financial Analysis:</strong><br>
                            {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
            
            # Chat input
            with st.form(key="indian_chat_form", clear_on_submit=True):
                user_input = st.text_area(
                    "Ask about financial performance, ratios, sector comparison, risks, or investment thesis:",
                    placeholder="E.g., What is the company's ROE compared to sector average? How is the debt situation? What are the growth drivers?",
                    height=120
                )
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    analysis_type = st.selectbox(
                        "Analysis Focus:",
                        ["General Analysis", "Profitability Focus", "Risk Assessment", "Valuation Metrics", "Sector Comparison"],
                        key="analysis_focus"
                    )
                
                with col2:
                    submit_button = st.form_submit_button("🔍 Analyze", use_container_width=True)
                
                if submit_button and user_input.strip():
                    # Add user message
                    st.session_state.chat_history.append({"role": "user", "content": user_input})
                    
                    # Generate AI response
                    with st.spinner("🧠 Generating financial analysis..."):
                        start_time = time.time()
                        
                        # Get relevant context
                        search_results = semantic_search_indian(user_input, top_k=3)
                        if search_results:
                            context = "\n\n".join([f"[Page {result['page_num']}] {result['text']}" for result in search_results])
                        else:
                            context = st.session_state.pdf_text[:1000]
                        
                        # Generate response
                        response = generate_indian_ai_response(user_input, context)
                        response_time = time.time() - start_time
                        
                        # Update metrics
                        update_metrics(response_time=response_time, success=True)
                        
                        # Add AI response
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                    
                    st.rerun()
        
        else:
            st.info("📤 Please upload an Indian financial document to begin analysis!")
            
            # Show sample documents info
            st.markdown("""
            ### 📋 Supported Indian Financial Documents:
            
            **📊 Company Filings:**
            - Annual Reports (Form 20-F)
            - Quarterly Results 
            - Investor Presentations
            - Corporate Governance Reports
            
            **🏛️ Exchange Filings:**
            - BSE/NSE announcements
            - Material disclosures
            - Board meeting outcomes
            
            **📈 Research Reports:**
            - Equity research reports
            - Sector analysis reports
            - Investment recommendations
            """)

# Sidebar enhancements
def create_sidebar():
    """Create sidebar with Indian market features"""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🇮🇳 Phase 2 Indian Features")
        
        features = [
            "✅ Indian Currency Recognition (₹, Crores, Lakhs)",
            "✅ Sector-Specific Analysis Templates",
            "✅ NSE/BSE Symbol Detection", 
            "✅ Indian Accounting Standards",
            "✅ Sector Benchmarking (IT, Banking, Pharma)",
            "✅ Indian Regulatory Context",
            "✅ Multi-language Support Preparation"
        ]
        
        for feature in features:
            st.markdown(f"<small>{feature}</small>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📈 Indian Market Metrics")
        
        if st.session_state.get('pdf_processed', False):
            company_info = st.session_state.get('company_info', {})
            if company_info.get('sector'):
                sector = company_info['sector']
                if sector in INDIAN_SECTOR_BENCHMARKS:
                    st.markdown(f"**{sector} Sector Averages:**")
                    benchmarks = INDIAN_SECTOR_BENCHMARKS[sector]
                    for metric, value in list(benchmarks.items())[:3]:
                        st.markdown(f"• {metric.replace('_', ' ').title()}: {value}")
        
        st.markdown("---")
        st.info("""
        **🚀 Enhanced for Indian Markets**
        
        This Phase 2 version is specifically optimized for:
        - Indian financial terminology
        - Sector-specific analysis
        - Regulatory compliance context
        - Currency and unit recognition
        - Market benchmark comparisons
        """)

if __name__ == "__main__":
    # Initialize session state at the very beginning
    init_session_state()
    main()
    create_sidebar()