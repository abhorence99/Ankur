#!/usr/bin/env uv run python
"""
APRA AMCOS Manual Search Parser

Use this when you've manually saved search results from the website.
1. Go to https://www.apraamcos.com.au/works-search
2. Search for your song manually
3. Save the results page as HTML (Ctrl+S / Cmd+S)
4. Run this script on the saved file
"""

import argparse
import sys
import re
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup


def parse_saved_results(html_file_path: str) -> Dict[str, Any]:
    """Parse results from a manually saved HTML file"""
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        return {
            'found': False,
            'count': 0,
            'results': [],
            'message': f'File not found: {html_file_path}'
        }
    except Exception as e:
        return {
            'found': False,
            'count': 0,
            'results': [],
            'message': f'Error reading file: {str(e)}'
        }
    
    return parse_search_results(html_content, html_file_path)


def parse_search_results(html_content: str, source: str) -> Dict[str, Any]:
    """Parse HTML content for search results"""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for results count
    results_header = soup.find('h6', string=re.compile(r'\d+\s+results?'))
    
    if not results_header:
        # Check if we have any work containers
        result_divs = soup.find_all('div', id=re.compile(r'^GW\d+'))
        if result_divs:
            return {
                'found': True,
                'count': len(result_divs),
                'results': [parse_single_result(div) for div in result_divs if parse_single_result(div)],
                'message': f'Found {len(result_divs)} result(s)',
                'source': source
            }
        else:
            return {
                'found': False,
                'count': 0,
                'results': [],
                'message': 'No results found in HTML file',
                'source': source
            }
    
    # Extract count
    count_match = re.search(r'(\d+)\s+results?', results_header.get_text())
    count = int(count_match.group(1)) if count_match else 0
    
    if count == 0:
        return {
            'found': False,
            'count': 0,
            'results': [],
            'message': 'Search returned 0 results',
            'source': source
        }
    
    # Parse individual results
    results = []
    result_divs = soup.find_all('div', id=re.compile(r'^GW\d+'))
    
    for result_div in result_divs:
        result_data = parse_single_result(result_div)
        if result_data:
            results.append(result_data)
    
    return {
        'found': len(results) > 0,
        'count': len(results),
        'results': results,
        'message': f'Found {len(results)} result(s)',
        'source': source
    }


def parse_single_result(result_div) -> Optional[Dict[str, Any]]:
    """Parse a single search result"""
    
    try:
        result = {
            'work_id': result_div.get('id', ''),
            'title': '',
            'writers': [],
            'performers': [],
            'publishers': [],
            'amcos_control': '',
            'alternate_titles': [],
            'local_work': False
        }
        
        # Extract title
        title_h4 = result_div.find('h4')
        if title_h4:
            result['title'] = ''.join(title_h4.stripped_strings)
        
        # Parse list items
        list_items = result_div.find_all('li', class_='grid')
        
        for item in list_items:
            label_div = item.find('div', class_='font-medium')
            content_div = item.find('div', class_='caption')
            
            if not label_div or not content_div:
                continue
                
            label = label_div.get_text(strip=True).lower()
            
            if 'writers' in label:
                writers = []
                writer_list = content_div.find('ul')
                if writer_list:
                    for li in writer_list.find_all('li'):
                        writer_name = ''.join(li.stripped_strings)
                        if writer_name:
                            writers.append(writer_name)
                result['writers'] = writers
                
            elif 'work id' in label:
                result['work_id'] = content_div.get_text(strip=True)
                
            elif 'amcos control' in label:
                result['amcos_control'] = content_div.get_text(strip=True)
                
            elif 'alternate titles' in label:
                titles = []
                title_list = content_div.find('ul')
                if title_list:
                    for li in title_list.find_all('li'):
                        titles.append(li.get_text(strip=True))
                result['alternate_titles'] = titles
                
            elif 'publishers' in label:
                publishers = []
                pub_list = content_div.find('ul')
                if pub_list:
                    for li in pub_list.find_all('li'):
                        pub_text = li.get_text(strip=True)
                        # Clean APRA/AMCOS indicators
                        pub_clean = re.sub(r'- APRA.*?- AMCOS.*?$', '', pub_text).strip()
                        publishers.append(pub_clean)
                result['publishers'] = publishers
                
            elif 'local work' in label:
                has_green_tick = content_div.find('path', fill='#0B9C00')
                result['local_work'] = bool(has_green_tick)
                
            elif 'performers' in label:
                performers = []
                perf_list = content_div.find('ul')
                if perf_list:
                    for li in perf_list.find_all('li'):
                        perf_name = ''.join(li.stripped_strings)
                        if perf_name:
                            performers.append(perf_name)
                result['performers'] = performers
        
        return result
        
    except Exception as e:
        print(f"Error parsing result: {e}", file=sys.stderr)
        return None


def format_result_output(result: Dict[str, Any]) -> str:
    """Format a single result for display"""
    
    output = []
    output.append(f"Title: {result['title']}")
    output.append(f"Work ID: {result['work_id']}")
    output.append(f"AMCOS Control: {result['amcos_control']}")
    output.append(f"Local Work: {'Yes' if result['local_work'] else 'No'}")
    
    if result['writers']:
        output.append(f"Writers ({len(result['writers'])}): {', '.join(result['writers'])}")
    
    if result['performers']:
        perf_count = len(result['performers'])
        if perf_count <= 5:
            output.append(f"Performers ({perf_count}): {', '.join(result['performers'])}")
        else:
            output.append(f"Performers ({perf_count}): {', '.join(result['performers'][:5])}... (+{perf_count-5} more)")
    
    if result['publishers']:
        output.append(f"Publishers ({len(result['publishers'])}): {', '.join(result['publishers'])}")
    
    if result['alternate_titles']:
        output.append(f"Alternate Titles: {', '.join(result['alternate_titles'])}")
    
    return '\n'.join(output)


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description='Parse APRA AMCOS search results from saved HTML file',
        epilog="""
Usage:
1. Go to https://www.apraamcos.com.au/works-search
2. Search for your song manually  
3. Save the results page as HTML (Ctrl+S / Cmd+S)
4. Run: %(prog)s path/to/saved-results.html
        """)
    
    parser.add_argument('html_file', help='Path to saved HTML file with search results')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    result = parse_saved_results(args.html_file)
    
    if result['found']:
        print(f"Found {result['count']} result(s):")
        print("=" * 50)
        
        for i, res in enumerate(result['results'], 1):
            if i > 1:
                print("-" * 50)
            print(format_result_output(res))
        
        if args.verbose:
            print(f"\nParsed from: {result.get('source', '')}", file=sys.stderr)
    else:
        print(result['message'])
        sys.exit(1)


if __name__ == '__main__':
    main()