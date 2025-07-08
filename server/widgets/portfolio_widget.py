from jinja2 import Environment, FileSystemLoader
import os

def render_portfolio_widget():
    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), '..')))
    template = env.get_template('widgets/portfolio_widget.html')
    return template.render()
