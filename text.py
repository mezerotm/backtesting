import argparse
import sys
import requests
from bs4 import BeautifulSoup

def decode_google_doc_grid(url):
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    doc_content = soup.find('div', class_='doc-content')

    if not doc_content:
        raise ValueError("Could not find 'doc-content' div in the HTML.")

    text_spans = doc_content.find_all('span')
    raw_text = '\n'.join(span.get_text() for span in text_spans)
    data_items = [item.strip() for item in raw_text.split('\n') if item.strip()]

    if not data_items:
        raise ValueError("No data items extracted from the document.")

    try:
        start_index = data_items.index('y-coordinate') + 1
    except ValueError:
        start_index = 0

    points = []
    max_x, max_y = 0, 0
    
    items_to_parse = data_items[start_index:]
    it = iter(items_to_parse)

    for chunk in zip(it, it, it):
        try:
            x_str, char, y_str = chunk
            x, y = int(x_str), int(y_str)
            
            if x > 1000 or y > 1000:
                continue

            points.append((char, x, y))
            max_x = max(max_x, x)
            max_y = max(max_y, y)
        except ValueError:
            continue
            
    if not points:
        raise ValueError("No valid coordinate data found.")

    grid = [[' ' for _ in range(max_x + 1)] for _ in range(max_y + 1)]

    for char, x, y in points:
        grid[y][x] = char

    for row in grid:
        print(''.join(row))

def main():
    parser = argparse.ArgumentParser(
        description='Decode a secret message from a Google Doc grid URL.'
    )
    parser.add_argument('url', help='URL to the document containing the grid data')
    args = parser.parse_args()
    
    try:
        decode_google_doc_grid(args.url)
    except requests.RequestException as e:
        print(f"Error fetching document: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error parsing document data: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

# Example usage:
# python text.py "https://example.com/your-doc.txt"
