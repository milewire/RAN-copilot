"""
AI Feature D - Natural Language Query Module
Allows users to ask questions about KPI behavior in plain English.
"""
import os
from typing import Dict, Any, List, Optional
import re
import json
from pathlib import Path

# Try to load .env file if dotenv is available
try:
    from dotenv import load_dotenv
    # Try to load .env from backend directory (where main.py is)
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# Try to import OpenAI, but make it optional
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def answer_question(
    question: str,
    kpi_context: List[Dict[str, Any]],
    rca_result: Optional[Dict[str, Any]] = None,
    use_local: bool = True
) -> Dict[str, Any]:
    """
    Answer natural language questions about KPI data.
    
    Args:
        question: User's question in plain English
        kpi_context: KPI data for context
        rca_result: Optional RCA results for additional context
        use_local: Use local model (default) or remote GPT
    
    Returns:
        Dictionary with:
        - answer: String answer to the question
        - confidence: Float between 0.0 and 1.0
    """
    # Check if cloud is allowed
    allow_cloud = os.getenv("ALLOW_CLOUD", "0") == "1"
    api_key = os.getenv("OPENAI_API_KEY", "")
    
    # Debug logging (can be removed in production)
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Ask AI - use_local={use_local}, allow_cloud={allow_cloud}, has_api_key={bool(api_key)}")
    
    # Use remote if: not using local mode AND cloud is allowed AND API key exists
    if not use_local and allow_cloud and api_key:
        return _answer_remote(question, kpi_context, rca_result)
    else:
        # If we wanted to use remote but can't, provide helpful error message
        if not use_local and (not allow_cloud or not api_key):
            if not allow_cloud:
                return {
                    "answer": "LLM mode is requested but ALLOW_CLOUD is not set to '1'. Please set ALLOW_CLOUD=1 in your .env file or environment variables.",
                    "confidence": 0.0
                }
            elif not api_key:
                return {
                    "answer": "LLM mode is requested but OPENAI_API_KEY is not configured. Please set OPENAI_API_KEY in your .env file or environment variables.",
                    "confidence": 0.0
                }
        return _answer_local(question, kpi_context, rca_result)


def _answer_local(
    question: str,
    kpi_context: List[Dict[str, Any]],
    rca_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Answer questions using local rule-based approach (no external LLM).
    """
    question_lower = question.lower()
    
    # Extract KPI statistics
    kpi_stats = {}
    for entry in kpi_context:
        kpi = entry.get("kpi", "")
        value = entry.get("value", 0)
        if kpi not in kpi_stats:
            kpi_stats[kpi] = []
        kpi_stats[kpi].append(value)
    
    # Calculate means
    kpi_means = {kpi: sum(values) / len(values) for kpi, values in kpi_stats.items() if values}
    
    # Question patterns and answers
    answer = ""
    confidence = 0.7  # Default confidence
    
    # Root cause questions
    if any(word in question_lower for word in ["root cause", "what is wrong", "issue", "problem"]):
        if rca_result:
            root_cause = rca_result.get("root_cause", "Unknown")
            severity = rca_result.get("severity", "low")
            answer = f"The primary root cause is: {root_cause} (Severity: {severity.upper()}). "
            if rca_result.get("recommendations"):
                answer += f"Recommended actions include: {rca_result['recommendations'][0]}"
            confidence = 0.9
        else:
            answer = "Root cause analysis is not available. Please run an analysis first."
            confidence = 0.5
    
    # KPI value questions
    elif any(word in question_lower for word in ["what is", "value of", "how much", "average"]):
        # Extract KPI name from question
        for kpi in kpi_means.keys():
            if kpi.lower().replace("_", " ") in question_lower or any(
                word in question_lower for word in kpi.lower().split("_")
            ):
                mean_val = kpi_means[kpi]
                answer = f"The average value for {kpi} is {mean_val:.2f}."
                confidence = 0.85
                break
        
        if not answer:
            # General KPI summary
            if kpi_means:
                top_kpi = max(kpi_means.items(), key=lambda x: x[1])
                answer = f"Key performance indicators show {top_kpi[0]} at {top_kpi[1]:.2f} on average."
                confidence = 0.7
    
    # Trend questions
    elif any(word in question_lower for word in ["trend", "increasing", "decreasing", "improving", "getting worse"]):
        if len(kpi_context) > 1:
            # Simple trend detection
            first_half = kpi_context[:len(kpi_context)//2]
            second_half = kpi_context[len(kpi_context)//2:]
            
            first_avg = sum(e.get("value", 0) for e in first_half) / len(first_half) if first_half else 0
            second_avg = sum(e.get("value", 0) for e in second_half) / len(second_half) if second_half else 0
            
            if second_avg > first_avg * 1.1:
                answer = "The metrics show an improving trend over the observed period."
            elif second_avg < first_avg * 0.9:
                answer = "The metrics show a declining trend over the observed period."
            else:
                answer = "The metrics appear relatively stable over the observed period."
            confidence = 0.75
        else:
            answer = "Insufficient data to determine trends. More data points are needed."
            confidence = 0.5
    
    # Anomaly questions
    elif any(word in question_lower for word in ["anomaly", "unusual", "abnormal", "outlier"]):
        if rca_result and rca_result.get("anomalies"):
            anomaly_count = len(rca_result["anomalies"])
            answer = f"Analysis detected {anomaly_count} anomaly(ies). "
            if anomaly_count > 0:
                top_anomaly = rca_result["anomalies"][0]
                answer += f"Most significant: {top_anomaly.get('kpi', 'Unknown')} with value {top_anomaly.get('value', 0):.2f}."
            confidence = 0.85
        else:
            answer = "No significant anomalies detected in the current data."
            confidence = 0.7
    
    # Site comparison questions
    elif any(word in question_lower for word in ["compare", "difference", "better", "worse", "best", "worst"]):
        sites = {}
        for entry in kpi_context:
            site = entry.get("site", "Unknown")
            kpi = entry.get("kpi", "")
            value = entry.get("value", 0)
            if site not in sites:
                sites[site] = {}
            if kpi not in sites[site]:
                sites[site][kpi] = []
            sites[site][kpi].append(value)
        
        if len(sites) > 1:
            # Compare sites
            site_avgs = {
                site: sum(sum(kpis.values(), [])) / sum(len(v) for v in kpis.values())
                for site, kpis in sites.items()
            }
            best_site = max(site_avgs.items(), key=lambda x: x[1])
            answer = f"Among the sites analyzed, {best_site[0]} shows the best average performance ({best_site[1]:.2f})."
            confidence = 0.8
        else:
            answer = "Only one site is available for comparison. Multiple sites are needed for comparison."
            confidence = 0.6
    
    # Default answer
    else:
        answer = "I can help you understand KPI metrics, root causes, trends, and anomalies. "
        answer += "Please try asking about specific KPIs, root causes, or trends in the data."
        if kpi_means:
            answer += f" Available KPIs include: {', '.join(list(kpi_means.keys())[:3])}."
        confidence = 0.5
    
    return {
        "answer": answer,
        "confidence": confidence
    }


def _answer_remote(
    question: str,
    kpi_context: List[Dict[str, Any]],
    rca_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Answer questions using remote GPT-4o API (only if ALLOW_CLOUD=1 and OPENAI_API_KEY is set).
    Falls back to local answer if API key is missing or API call fails.
    """
    # Check if OpenAI is available
    if not OPENAI_AVAILABLE:
        return {
            "answer": "OpenAI library not installed. Install with: pip install openai",
            "confidence": 0.0
        }
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "answer": "OpenAI API key not configured. Set OPENAI_API_KEY environment variable to use GPT-4o. Falling back to local analysis.",
            "confidence": 0.0
        }
    
    try:
        # Initialize OpenAI client - strip API key to remove any whitespace
        api_key_clean = api_key.strip()
        # Only pass api_key, let OpenAI handle other config from environment
        client = OpenAI(api_key=api_key_clean)
        
        # Prepare context for the LLM
        context_parts = []
        
        # Add KPI summary
        if kpi_context:
            kpi_stats = {}
            for entry in kpi_context:
                kpi = entry.get("kpi", "")
                value = entry.get("value", 0)
                site = entry.get("site", "Unknown")
                timestamp = entry.get("timestamp", "")
                if kpi not in kpi_stats:
                    kpi_stats[kpi] = []
                kpi_stats[kpi].append({"value": value, "site": site, "timestamp": timestamp})
            
            # Calculate statistics
            kpi_summary = {}
            for kpi, values in kpi_stats.items():
                vals = [v["value"] for v in values]
                if vals:
                    kpi_summary[kpi] = {
                        "mean": sum(vals) / len(vals),
                        "min": min(vals),
                        "max": max(vals),
                        "count": len(vals),
                        "sites": list(set(v["site"] for v in values))
                    }
            
            context_parts.append(f"KPI Data Summary:\n{json.dumps(kpi_summary, indent=2)}")
        
        # Add RCA results if available
        if rca_result:
            rca_summary = {
                "root_cause": rca_result.get("root_cause", "Unknown"),
                "severity": rca_result.get("severity", "low"),
                "anomalies_count": len(rca_result.get("anomalies", [])),
                "recommendations": rca_result.get("recommendations", [])[:3]  # Top 3
            }
            context_parts.append(f"RCA Analysis Results:\n{json.dumps(rca_summary, indent=2)}")
        
        # Build the prompt
        system_prompt = """You are an expert LTE network analyst specializing in Band 41 performance monitoring. 
You analyze KPI (Key Performance Indicator) data from Ericsson ENM systems to help diagnose network issues.

Your role:
- Answer questions about KPI metrics, trends, and anomalies
- Explain root causes based on RCA (Root Cause Analysis) results
- Provide clear, technical but accessible explanations
- Reference specific KPI values and thresholds when relevant
- Generate professional, report-quality responses suitable for network operations teams

Common KPIs you'll see:
- RRC_Setup_Success_Rate (target: ≥95%)
- ERAB_Setup_Success_Rate (target: ≥98%)
- PRB_Utilization_Avg (target: <70%)
- SINR_Avg (target: >5 dB)
- BLER_P95 (target: <10%)
- Paging_Success_Rate (target: ≥95%)

CRITICAL FORMATTING RULES - STRICTLY ENFORCED:
- ABSOLUTELY NO LaTeX notation - this will not render in the interface
- NEVER use: \[, \], \(, \), \text{}, \frac{}, \times, or any LaTeX commands
- For formulas, use plain text: "RRC Setup Success Rate = (RRC Setup Success / RRC Setup Attempts) × 100"
- For calculations, use: "RRC Setup Success Rate = (128/140) × 100 = 91.43%"
- Use × for multiplication (not \times), ÷ for division
- Write formulas inline with text, not as separate blocks
- Example CORRECT format: "The RRC Setup Success Rate is calculated as (128/140) × 100 = 91.43%"
- Example WRONG format: "\[ \text{RRC Setup Success Rate} = \left( \frac{128}{140} \right) \times 100 \]" (DO NOT USE THIS)
- Avoid excessive blank lines between sections (use single line breaks)
- Structure responses with clear headings using **bold** for emphasis
- Use numbered lists (1., 2., 3.) for multiple recommendations
- Be concise but thorough - each point should be actionable
- Include specific site IDs, KPI values, and thresholds in your analysis
- Write in a professional, technical tone suitable for network engineers

Response Structure Guidelines:
- Start with a brief summary if the question is broad
- Use clear section headers with **bold** text
- Provide specific calculations with actual values
- Include actionable recommendations with clear next steps
- Reference thresholds and targets when discussing KPIs
- End with a brief conclusion summarizing key actions"""

        user_prompt = f"""Context:
{chr(10).join(context_parts) if context_parts else "No specific context available."}

Question: {question}

Please provide a clear, technical answer based on the KPI data and RCA results provided above."""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent, factual responses
            max_tokens=500
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Clean up any LaTeX notation that might have slipped through
        import re
        # Remove LaTeX display math blocks \[ ... \]
        answer = re.sub(r'\\\[.*?\\\]', '', answer, flags=re.DOTALL)
        # Remove LaTeX inline math \( ... \)
        answer = re.sub(r'\\\(.*?\\\)', '', answer)
        # Remove LaTeX text commands \text{...}
        answer = re.sub(r'\\text\{([^}]+)\}', r'\1', answer)
        # Remove LaTeX frac commands \frac{a}{b} -> a/b
        answer = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1/\2)', answer)
        # Remove LaTeX left/right delimiters
        answer = re.sub(r'\\left\(|\\right\)', '(', answer)
        answer = re.sub(r'\\left\[|\\right\]', '[', answer)
        # Remove LaTeX times command \times -> ×
        answer = answer.replace('\\times', '×')
        # Clean up multiple spaces and blank lines
        answer = re.sub(r'\n\s*\n\s*\n+', '\n\n', answer)
        answer = answer.strip()
        
        confidence = 0.9  # High confidence for GPT-4o responses
        
        return {
            "answer": answer,
            "confidence": confidence
        }
    
    except Exception as e:
        # Fall back to local answer on any error
        error_msg = str(e)
        return {
            "answer": f"Error calling OpenAI API: {error_msg}. Falling back to local analysis.",
            "confidence": 0.0
        }

