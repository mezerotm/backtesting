import os
import traceback
from typing import Dict, Any, Optional
from utils.config import OPENAI_API_KEY
import openai
import json

def validate_api_key(api_key):
    """Validate the API key format and print helpful messages"""
    if not api_key:
        print("API key is empty")
        return False
    
    return True

class AIExplainer:
    """Class to generate AI explanations for backtest results using OpenAI API."""
    
    def __init__(self):
        """Initialize the AIExplainer with the OpenAI API key from config."""
        self.api_key = OPENAI_API_KEY
        if not self.api_key:
            print("Warning: No OpenAI API key found in config. AI explanations will not be available.")
        else:
            # Remove debugging statements
            if validate_api_key(self.api_key):
                print("OpenAI API key validated.")
            else:
                print("API key validation failed. AI explanations will not work correctly.")
    
    def can_generate_explanations(self) -> bool:
        """Check if explanations can be generated (API key is available)."""
        return bool(self.api_key)
    
    def explain_metric(self, metric_name: str, metric_value: Any, strategy_name: str, 
                       metric_context: Dict[str, Any] = None) -> str:
        """Generate an explanation for a specific metric value.
        
        Args:
            metric_name: Name of the metric (e.g. 'Return [%]')
            metric_value: Value of the metric
            strategy_name: Name of the strategy
            metric_context: Additional context about other metrics for this strategy
            
        Returns:
            A string containing the AI explanation
        """
        if not self.can_generate_explanations():
            return "AI explanations not available (no API key)"
        
        try:
            # Create a prompt for the OpenAI API
            prompt = self._create_prompt(metric_name, metric_value, strategy_name, metric_context)
            
            # Debug output
            print(f"Generating explanation for {metric_name} = {metric_value}")
            
            # Use the modern OpenAI API
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial trading expert explaining backtest results concisely."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.5,
            )
            explanation = response.choices[0].message.content
            
            return explanation.strip()
            
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"Error generating AI explanation for {metric_name}: {e}")
            print(f"Detailed error: {error_details}")
            return f"Could not generate explanation: {str(e)}"
    
    def explain_strategy_overview(self, strategy_name: str, metrics: Dict[str, Any]) -> str:
        """Generate an overall explanation for a strategy based on all its metrics.
        
        Args:
            strategy_name: Name of the strategy
            metrics: Dictionary of all metrics for this strategy
            
        Returns:
            A string containing the AI explanation
        """
        if not self.can_generate_explanations():
            return "AI explanations not available (no API key)"
        
        try:
            # Create a comprehensive prompt about the entire strategy
            metrics_text = "\n".join([f"{k}: {v}" for k, v in metrics.items()])
            prompt = f"""
            Analyze the following backtest results for the trading strategy '{strategy_name}':
            
            {metrics_text}
            
            Provide a brief (2-3 sentences) explanation of how this strategy performed, highlighting key strengths and weaknesses.
            """
            
            # Debug output
            print(f"Generating strategy overview for {strategy_name}")
            
            # Use the modern OpenAI API
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial trading expert explaining backtest results concisely."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7,
            )
            explanation = response.choices[0].message.content
            
            return explanation.strip()
            
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"Error generating strategy overview for {strategy_name}: {e}")
            print(f"Detailed error: {error_details}")
            return f"Could not generate strategy overview: {str(e)}"
    
    def _create_prompt(self, metric_name: str, metric_value: Any, strategy_name: str, 
                      metric_context: Dict[str, Any] = None) -> str:
        """Create a prompt for the OpenAI API based on the metric and its value.
        
        Args:
            metric_name: Name of the metric
            metric_value: Value of the metric
            strategy_name: Name of the strategy
            metric_context: Additional context about other metrics for this strategy
            
        Returns:
            A string prompt for the OpenAI API
        """
        # Base prompt about the metric
        prompt = f"Explain what it means that the '{metric_name}' for the trading strategy '{strategy_name}' is {metric_value}."
        
        # Add context about other metrics if available
        if metric_context:
            context_text = "\n".join([f"{k}: {v}" for k, v in metric_context.items() if k != metric_name])
            prompt += f"\n\nOther metrics for this strategy:\n{context_text}"
            prompt += "\n\nKeep your explanation focused on the specified metric, but use this context if relevant."
        
        # Add specific instructions based on the metric
        if "Return" in metric_name:
            prompt += "\nComment on whether this return is good or poor."
        elif "Drawdown" in metric_name:
            prompt += "\nExplain what this drawdown means for risk."
        elif "Ratio" in metric_name:
            prompt += "\nExplain what this ratio value indicates about strategy performance."
        
        prompt += "\nKeep your explanation very concise (1-2 sentences maximum)."
        
        return prompt 

def load_metadata(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def get_reports(directory='public/results'):
    # List all JSON files in the specified directory
    report_files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.endswith('.json')
    ]

    reports = []
    for file_path in report_files:
        metadata = load_metadata(file_path)
        if metadata.get('status') == 'finished':
            reports.append(metadata)

    return reports

def display_reports():
    reports = get_reports()
    for report in reports:
        # Display logic here
        print(f"Symbol: {report['symbol']}, Date Range: {report['date_range']}") 