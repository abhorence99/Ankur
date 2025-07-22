#!/usr/bin/env uv run python
"""
APRA AMCOS Song Catalogue Search Script (Final Version)

Searches the APRA AMCOS catalogue for songs by title, writer surname, or performer name.
Can be used from command line for single searches or imported for batch processing.
"""

import argparse
import sys
import urllib.parse
import re
from typing import Dict, List, Optional, Any
import requests
from bs4 import BeautifulSoup


def search_apra_catalogue(title: Optional[str] = None, 
                         writer_surname: Optional[str] = None, 
                         performer: Optional[str] = None) -> Dict[str, Any]:
    """
    Search APRA AMCOS Song Catalogue
    
    Args:
        title: Song title to search for
        writer_surname: Writer's surname (last name only)
        performer: Performer name
    
    Returns:
        dict with:
            - 'found': bool - whether results were found
            - 'count': int - number of results
            - 'results': list - parsed result details
            - 'message': str - status message
    """
    
    # Ensure at least title or performer is provided
    if not title and not performer:
        return {
            'found': False,
            'count': 0,
            'results': [],
            'message': 'Error: Title or performer is required for search'
        }
    
    # Create session for cookie handling
    session = requests.Session()
    
    try:
        # First, visit the search page to get any necessary cookies/session data
        base_url = "https://www.apraamcos.com.au/works-search"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        }
        
        # Get the initial page
        response = session.get(base_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Now try the search with parameters
        params = {'works': 'true'}
        
        if title:
            params['title'] = title
        if writer_surname:
            params['writer'] = writer_surname  
        if performer:
            params['performer'] = performer
        
        # Try both GET and POST approaches
        search_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        # Update headers for search request
        headers.update({
            'Referer': base_url,
            'Sec-Fetch-Site': 'same-origin',
        })
        
        # Try GET request first
        search_response = session.get(search_url, headers=headers, timeout=30)
        search_response.raise_for_status()
        
        # Parse the response
        result = parse_search_results(search_response.text, search_url)
        
        # If GET didn't work, try POST
        if not result['found']:
            headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
            })
            
            post_response = session.post(base_url, data=params, headers=headers, timeout=30)
            post_response.raise_for_status()
            
            result = parse_search_results(post_response.text, search_url)
        
        return result
        
    except requests.exceptions.RequestException as e:
        return {
            'found': False,
            'count': 0,
            'results': [],
            'message': f'Network error: {str(e)}'
        }
    except Exception as e:
        return {
            'found': False,
            'count': 0,
            'results': [],
            'message': f'Error: {str(e)}'
        }


def parse_search_results(html_content: str, search_url: str) -> Dict[str, Any]:
    """Parse HTML response to extract search results"""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for results count
    results_header = soup.find('h6', string=re.compile(r'\d+\s+results?'))
    
    if not results_header:
        return {
            'found': False,
            'count': 0,
            'results': [],
            'message': 'No results found'
        }
    
    # Extract count
    count_match = re.search(r'(\d+)\s+results?', results_header.get_text())
    count = int(count_match.group(1)) if count_match else 0
    
    if count == 0:
        return {
            'found': False,
            'count': 0,
            'results': [],
            'message': 'No results found'
        }
    
    # Parse individual results
    results = []
    
    # Find result containers (divs with IDs starting with GW)
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
        'search_url': search_url
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
            # Remove highlight spans and get clean text
            result['title'] = ''.join(title_h4.stripped_strings)
        
        # Parse all list items for different fields
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
                            # Clean up writer names that might be concatenated
                            writers.append(clean_name(writer_name))
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
                        title_text = li.get_text(strip=True)
                        if title_text:
                            titles.append(title_text)
                else:
                    # Handle case where titles are not in a list
                    title_text = content_div.get_text(strip=True)
                    if title_text and title_text != result['title']:
                        titles = [title_text]
                result['alternate_titles'] = titles
                
            elif 'publishers' in label:
                publishers = []
                pub_list = content_div.find('ul')
                if pub_list:
                    for li in pub_list.find_all('li'):
                        pub_name = li.get_text(strip=True)
                        if pub_name:
                            # Clean up publisher info (remove APRA/AMCOS indicators)
                            pub_name = re.sub(r'- APRA.*?- AMCOS.*?$', '', pub_name).strip()
                            publishers.append(pub_name)
                result['publishers'] = publishers
                
            elif 'local work' in label:
                # Check for green tick (positive) vs red cross (negative)
                has_green_tick = content_div.find('path', fill='#0B9C00')
                result['local_work'] = bool(has_green_tick)
                
            elif 'performers' in label:
                performers = []
                perf_list = content_div.find('ul')
                if perf_list:
                    for li in perf_list.find_all('li'):
                        perf_name = ''.join(li.stripped_strings)
                        if perf_name:
                            performers.append(clean_name(perf_name))
                result['performers'] = performers
        
        return result
        
    except Exception as e:
        print(f"Error parsing result: {e}", file=sys.stderr)
        return None


def clean_name(name: str) -> str:
    """Clean up concatenated or formatted names"""
    # For now, just return as-is, but could add logic to split concatenated names
    return name


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
        description='Search APRA AMCOS Song Catalogue',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --title "ordinary" --performer "alex warren"
  %(prog)s --title "bohemian rhapsody" --writer "mercury"  
  %(prog)s --performer "the beatles"
        """)
    
    parser.add_argument('--title', '-t', help='Song title to search for')
    parser.add_argument('--writer', '-w', help='Writer surname (last name only)')
    parser.add_argument('--performer', '-p', help='Performer name')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Check that at least title or performer is provided
    if not args.title and not args.performer:
        parser.error("Either --title or --performer must be specified")
    
    # Perform search
    if args.verbose:
        print(f"Searching for:", file=sys.stderr)
        if args.title:
            print(f"  Title: {args.title}", file=sys.stderr)
        if args.writer:
            print(f"  Writer: {args.writer}", file=sys.stderr)
        if args.performer:
            print(f"  Performer: {args.performer}", file=sys.stderr)
        print(file=sys.stderr)
    
    result = search_apra_catalogue(
        title=args.title,
        writer_surname=args.writer,
        performer=args.performer
    )
    
    # Display results
    if result['found']:
        print(f"Found {result['count']} result(s):")
        print("=" * 50)
        
        for i, res in enumerate(result['results'], 1):
            if i > 1:
                print("-" * 50)
            print(format_result_output(res))
        
        if args.verbose:
            print(f"\nSearch URL: {result.get('search_url', '')}", file=sys.stderr)
    else:
        print(result['message'])
        sys.exit(1)


if __name__ == '__main__':
    main()