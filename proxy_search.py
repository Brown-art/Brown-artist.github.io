from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup
import urllib.parse

app = Flask(__name__)

# Basic layout template
LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Private Research Tool</title>
    <style>
        body { font-family: -apple-system, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; background: #fafafa; color: #333; }
        .search-box { display: flex; gap: 10px; margin-bottom: 30px; }
        input[type="text"] { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 16px; }
        input[type="submit"] { padding: 12px 24px; background: #0076ff; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; }
        .article { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }
        h1, h2 { color: #111; }
        a { color: #0076ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    {{ content|safe }}
</body>
</html>
"""

@app.route('/')
def index():
    home_html = """
    <h2 style="text-align: center; margin-top: 50px;">Text-Only Research Lookup</h2>
    <form action="/search" method="get" class="search-box">
        <input type="text" name="q" placeholder="Enter keywords to look up..." required autofocus>
        <input type="submit" value="Search">
    </form>
    """
    return LAYOUT.replace('{{ content|safe }}', home_html)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return "Please input a search term.", 400

    # Uses a fallback text scraper engine to pull standard search summaries safely
    search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        res = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        results_html = ['<h2>Results for: {}</h2><div class="search-box"><form action="/search" method="get" style="width:100%; display:flex; gap:10px;"><input type="text" name="q" value="{}" required><input type="submit" value="Search"></form></div>'.format(query, query)]
        
        # Scrape links out of the HTML result structure
        for links in soup.find_all('a', class_='result__url'):
            title_node = links.find_previous('a', class_='result__snippet')
            title = title_node.text if title_node else "View Article Text"
            raw_href = links.get('href', '')
            
            # Clean up out-of-bounds tracking variables from search links
            parsed = urllib.parse.urlparse(raw_href)
            actual_url = urllib.parse.parse_qs(parsed.query).get('uddg', [''])
            
            if actual_url:
                results_html.append(f"""
                <div class="article">
                    <h3><a href="/view?url={urllib.parse.quote(actual_url[0])}">{title}</a></h3>
                    <p style="color: #666; font-size: 14px;">Source: {actual_url[0]}</p>
                </div>
                """)
                
        if len(results_html) <= 1:
            results_html.append("<p>No plain text files found for this query. Try different keywords.</p>")
            
        return LAYOUT.replace('{{ content|safe }}', "".join(results_html))
    except Exception as e:
        return f"Lookup Failed: {str(e)}", 500

@app.route('/view')
def view():
    target_url = request.args.get('url', '')
    if not target_url:
        return "Missing URL path.", 400
        
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(target_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Completely strip out games, visual frames, popups, and scripts
        for element in soup(["script", "style", "iframe", "nav", "footer", "header", "form"]):
            element.decompose()
            
        # Extract title and body elements to build a completely clean reading layout
        title = soup.title.text if soup.title else "Document View"
        body_text = []
        
        for paragraph in soup.find_all(['h1', 'h2', 'h3', 'p']):
            text = paragraph.get_text().strip()
            if text and len(text) > 10:
                body_text.append(f"<{paragraph.name}>{text}</{paragraph.name}>")
                
        clean_content = f"""
        <a href="javascript:history.back()">← Back to Search Results</a>
        <h1>{title}</h1>
        <hr style="border: 0; border-top: 1px solid #eee; margin-bottom: 20px;">
        {"".join(body_text) if body_text else "<p>This page could not be parsed into plain text.</p>"}
        """
        return LAYOUT.replace('{{ content|safe }}', clean_content)
    except Exception as e:
        return f"Unable to display page text: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
