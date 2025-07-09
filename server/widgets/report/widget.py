from jinja2 import Environment, FileSystemLoader
import os

def render_report_widget():
    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), '..')))
    template = env.get_template('widgets/report_widget.html')
    return template.render()
