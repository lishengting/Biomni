import logging
import os
import re
import time
from io import BytesIO
from urllib.parse import urljoin

import PyPDF2
import requests
from bs4 import BeautifulSoup
from googlesearch import search

# Configure logger
logger = logging.getLogger(__name__)

# Global debug flag
DEBUG_MODE = True


def set_debug_mode(debug: bool):
    """Set the debug mode for logging network requests.
    
    Args:
        debug (bool): True to enable debug logging, False to disable
    """
    global DEBUG_MODE
    DEBUG_MODE = debug


def fetch_supplementary_info_from_doi(doi: str, output_dir: str = "supplementary_info"):
    """Fetches supplementary information for a paper given its DOI and returns a research log.

    Args:
        doi: The paper DOI.
        output_dir: Directory to save supplementary files.

    Returns:
        dict: A dictionary containing a research log and the downloaded file paths.

    """
    research_log = []
    research_log.append(f"Starting process for DOI: {doi}")
    
    # Log the process if debug mode is enabled
    if DEBUG_MODE:
        logger.debug(f"Starting supplementary info fetch for DOI: {doi}")

    # CrossRef API to resolve DOI to a publisher page
    crossref_url = f"https://doi.org/{doi}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    if DEBUG_MODE:
        logger.debug(f"Resolving DOI via CrossRef API: {crossref_url}")
    
    response = requests.get(crossref_url, headers=headers)

    if response.status_code != 200:
        log_message = f"Failed to resolve DOI: {doi}. Status Code: {response.status_code}"
        research_log.append(log_message)
        
        if DEBUG_MODE:
            logger.error(f"Failed to resolve DOI: {doi}. Status Code: {response.status_code}")
        
        return {"log": research_log, "files": []}

    publisher_url = response.url
    research_log.append(f"Resolved DOI to publisher page: {publisher_url}")
    
    if DEBUG_MODE:
        logger.debug(f"DOI resolved to publisher page: {publisher_url}")

    # Fetch publisher page
    if DEBUG_MODE:
        logger.debug(f"Fetching publisher page: {publisher_url}")
    
    response = requests.get(publisher_url, headers=headers)
    if response.status_code != 200:
        log_message = f"Failed to access publisher page for DOI {doi}."
        research_log.append(log_message)
        return {"log": research_log, "files": []}

    # Parse page content
    if DEBUG_MODE:
        logger.debug("Parsing publisher page content")
    
    soup = BeautifulSoup(response.content, "html.parser")
    supplementary_links = []

    # Look for supplementary materials by keywords or links
    for link in soup.find_all("a", href=True):
        href = link.get("href")
        text = link.get_text().lower()
        if "supplementary" in text or "supplemental" in text or "appendix" in text:
            full_url = urljoin(publisher_url, href)
            supplementary_links.append(full_url)
            research_log.append(f"Found supplementary material link: {full_url}")
            
            if DEBUG_MODE:
                logger.debug(f"Found supplementary material link: {full_url}")

    if not supplementary_links:
        log_message = f"No supplementary materials found for DOI {doi}."
        research_log.append(log_message)
        
        if DEBUG_MODE:
            logger.debug(f"No supplementary materials found for DOI {doi}")
        
        return research_log

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    research_log.append(f"Created output directory: {output_dir}")
    
    if DEBUG_MODE:
        logger.debug(f"Created output directory: {output_dir}")

    # Download supplementary materials
    downloaded_files = []
    for link in supplementary_links:
        file_name = os.path.join(output_dir, link.split("/")[-1])
        
        if DEBUG_MODE:
            logger.debug(f"Downloading file from: {link}")
        
        file_response = requests.get(link, headers=headers)
        if file_response.status_code == 200:
            with open(file_name, "wb") as f:
                f.write(file_response.content)
            downloaded_files.append(file_name)
            research_log.append(f"Downloaded file: {file_name}")
            
            if DEBUG_MODE:
                logger.debug(f"Successfully downloaded file: {file_name}")
        else:
            research_log.append(f"Failed to download file from {link}")
            
            if DEBUG_MODE:
                logger.error(f"Failed to download file from {link}. Status code: {file_response.status_code}")

    if downloaded_files:
        research_log.append(f"Successfully downloaded {len(downloaded_files)} file(s).")
        
        if DEBUG_MODE:
            logger.debug(f"Successfully downloaded {len(downloaded_files)} file(s)")
    else:
        research_log.append(f"No files could be downloaded for DOI {doi}.")
        
        if DEBUG_MODE:
            logger.debug(f"No files could be downloaded for DOI {doi}")

    return "\n".join(research_log)


def query_arxiv(query: str, max_papers: int = 10) -> str:
    """Query arXiv for papers based on the provided search query.

    Parameters
    ----------
    - query (str): The search query string.
    - max_papers (int): The maximum number of papers to retrieve (default: 10).

    Returns
    -------
    - str: The formatted search results or an error message.

    """
    import arxiv

    logger.debug(f"[进入] query_arxiv, query={query}, max_papers={max_papers}")
    try:
        client = arxiv.Client()
        search = arxiv.Search(query=query, max_results=max_papers, sort_by=arxiv.SortCriterion.Relevance)
        results = "\n\n".join([f"Title: {paper.title}\nSummary: {paper.summary}" for paper in client.results(search)])
        if results:
            logger.debug(f"[成功] query_arxiv, 返回结果数: {len(results.split('Title:'))-1}")
            return results
        else:
            logger.debug("[失败] query_arxiv, 未找到论文")
            return "No papers found on arXiv."
    except Exception as e:
        logger.error(f"[异常] query_arxiv: {e}")
        return f"Error querying arXiv: {e}"
#     try:
#         client = arxiv.Client()  # [已注释，原因：增加详细日志]
#         search = arxiv.Search(query=query, max_results=max_papers, sort_by=arxiv.SortCriterion.Relevance)
#         results = "\n\n".join([f"Title: {paper.title}\nSummary: {paper.summary}" for paper in client.results(search)])
#         return results if results else "No papers found on arXiv."
#     except Exception as e:
#         return f"Error querying arXiv: {e}"  # [已注释，原因：增加详细日志]


def query_scholar(query: str) -> str:
    """Query Google Scholar for papers based on the provided search query.

    Parameters
    ----------
    - query (str): The search query string.

    Returns
    -------
    - str: The first search result formatted or an error message.

    """
    from scholarly import scholarly

    logger.debug(f"[进入] query_scholar, query={query}")
    try:
        search_query = scholarly.search_pubs(query)
        result = next(search_query, None)
        if result:
            logger.debug(f"[成功] query_scholar, 返回结果: {result['bib'].get('title', '')}")
            return f"Title: {result['bib']['title']}\nYear: {result['bib']['pub_year']}\nVenue: {result['bib']['venue']}\nAbstract: {result['bib']['abstract']}"
        else:
            logger.debug("[失败] query_scholar, 未找到结果")
            return "No results found on Google Scholar."
    except Exception as e:
        logger.error(f"[异常] query_scholar: {e}")
        return f"Error querying Google Scholar: {e}"
#     try:
#         search_query = scholarly.search_pubs(query)  # [已注释，原因：增加详细日志]
#         result = next(search_query, None)
#         if result:
#             return f"Title: {result['bib']['title']}\nYear: {result['bib']['pub_year']}\nVenue: {result['bib']['venue']}\nAbstract: {result['bib']['abstract']}"
#         else:
#             return "No results found on Google Scholar."
#     except Exception as e:
#         return f"Error querying Google Scholar: {e}"  # [已注释，原因：增加详细日志]


def query_pubmed(query: str, max_papers: int = 10, max_retries: int = 3) -> str:
    """Query PubMed for papers based on the provided search query.

    Parameters
    ----------
    - query (str): The search query string.
    - max_papers (int): The maximum number of papers to retrieve (default: 10).
    - max_retries (int): Maximum number of retry attempts with modified queries (default: 3).

    Returns
    -------
    - str: The formatted search results or an error message.

    """
    from pymed import PubMed

    logger.debug(f"[进入] query_pubmed, query={query}, max_papers={max_papers}, max_retries={max_retries}")
    try:
        pubmed = PubMed(tool="MyTool", email="your-email@example.com")  # Update with a valid email address

        # Initial attempt
        papers = list(pubmed.query(query, max_results=max_papers))

        # Retry with modified queries if no results
        retries = 0
        while not papers and retries < max_retries:
            retries += 1
            simplified_query = " ".join(query.split()[:-retries]) if len(query.split()) > retries else query
            time.sleep(1)
            logger.debug(f"[重试] query_pubmed, simplified_query={simplified_query}, retries={retries}")
            papers = list(pubmed.query(simplified_query, max_results=max_papers))

        if papers:
            logger.debug(f"[成功] query_pubmed, 返回结果数: {len(papers)}")
            results = "\n\n".join(
                [f"Title: {paper.title}\nAbstract: {paper.abstract}\nJournal: {paper.journal}" for paper in papers]
            )
            return results
        else:
            logger.debug("[失败] query_pubmed, 多次尝试后未找到论文")
            return "No papers found on PubMed after multiple query attempts."
    except Exception as e:
        logger.error(f"[异常] query_pubmed: {e}")
        return f"Error querying PubMed: {e}"
#     try:
#         pubmed = PubMed(tool="MyTool", email="your-email@example.com")  # [已注释，原因：增加详细日志]
#         papers = list(pubmed.query(query, max_results=max_papers))
#         retries = 0
#         while not papers and retries < max_retries:
#             retries += 1
#             simplified_query = " ".join(query.split()[:-retries]) if len(query.split()) > retries else query
#             time.sleep(1)
#             papers = list(pubmed.query(simplified_query, max_results=max_papers))
#         if papers:
#             results = "\n\n".join(
#                 [f"Title: {paper.title}\nAbstract: {paper.abstract}\nJournal: {paper.journal}" for paper in papers]
#             )
#             return results
#         else:
#             return "No papers found on PubMed after multiple query attempts."
#     except Exception as e:
#         return f"Error querying PubMed: {e}"  # [已注释，原因：增加详细日志]


def search_google(query: str, num_results: int = 3, language: str = "en") -> list[dict]:
    """Search using Google search.

    Args:
        query (str): The search query (e.g., "protocol text or seach question")
        num_results (int): Number of results to return (default: 10)
        language (str): Language code for search results (default: 'en')
        pause (float): Pause between searches to avoid rate limiting (default: 2.0 seconds)

    Returns:
        List[dict]: List of dictionaries containing search results with title and URL

    """
    try:
        logger.debug(f"[进入] search_google, query={query}, num_results={num_results}, language={language}")
        results_string = ""
        search_query = f"{query}"

        for res in search(search_query, num_results=num_results, lang=language, advanced=True):
            title = res.title
            url = res.url
            description = res.description

            results_string += f"Title: {title}\nURL: {url}\nDescription: {description}\n\n"
        logger.debug(f"[成功] search_google, 返回结果数: {results_string.count('Title:')}")
    except Exception as e:
        logger.error(f"[异常] search_google: {str(e)}")
    return results_string
#     try:
#         results_string = ""  # [已注释，原因：增加详细日志]
#         search_query = f"{query}"
#         for res in search(search_query, num_results=num_results, lang=language, advanced=True):
#             title = res.title
#             url = res.url
#             description = res.description
#             results_string += f"Title: {title}\nURL: {url}\nDescription: {description}\n\n"
#     except Exception as e:
#         print(f"Error performing search: {str(e)}")  # [已注释，原因：增加详细日志]
#     return results_string


def extract_url_content(url: str) -> str:
    """Extract the text content of a webpage using requests and BeautifulSoup.

    Args:
        url: Webpage URL to extract content from

    Returns:
        Text content of the webpage

    """
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

    # Check if the response is in text format
    if "text/plain" in response.headers.get("Content-Type", "") or "application/json" in response.headers.get(
        "Content-Type", ""
    ):
        return response.text.strip()  # Return plain text or JSON response directly

    # If it's HTML, use BeautifulSoup to parse
    soup = BeautifulSoup(response.text, "html.parser")

    # Try to find main content first, fallback to body
    content = soup.find("main") or soup.find("article") or soup.body

    # Remove unwanted elements
    for element in content(["script", "style", "nav", "header", "footer", "aside", "iframe"]):
        element.decompose()

    # Extract text with better formatting
    paragraphs = content.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6"])
    cleaned_text = []

    for p in paragraphs:
        text = p.get_text().strip()
        if text:  # Only add non-empty paragraphs
            cleaned_text.append(text)

    return "\n\n".join(cleaned_text)


def extract_pdf_content(url: str) -> str:
    """Extract the text content of a PDF file given its URL.

    Args:
        url: URL of the PDF file to extract text from

    Returns:
        The extracted text content from the PDF

    """
    try:
        # Check if the URL ends with .pdf
        if not url.lower().endswith(".pdf"):
            # If not, try to find a PDF link on the page
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                # Look for PDF links in the HTML content
                pdf_links = re.findall(r'href=[\'"]([^\'"]+\.pdf)[\'"]', response.text)
                if pdf_links:
                    # Use the first PDF link found
                    if not pdf_links[0].startswith("http"):
                        # Handle relative URLs
                        base_url = "/".join(url.split("/")[:3])
                        url = base_url + pdf_links[0] if pdf_links[0].startswith("/") else base_url + "/" + pdf_links[0]
                    else:
                        url = pdf_links[0]
                else:
                    return f"No PDF file found at {url}. Please provide a direct link to a PDF file."

        # Download the PDF
        response = requests.get(url, timeout=30)

        # Check if we actually got a PDF file (by checking content type or magic bytes)
        content_type = response.headers.get("Content-Type", "").lower()
        if "application/pdf" not in content_type and not response.content.startswith(b"%PDF"):
            return f"The URL did not return a valid PDF file. Content type: {content_type}"

        pdf_file = BytesIO(response.content)

        # Try with PyPDF2 first
        try:
            text = ""
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")

        # Clean up the text
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            return "The PDF file did not contain any extractable text. It may be an image-based PDF requiring OCR."

        return text

    except requests.exceptions.RequestException as e:
        return f"Error downloading PDF: {str(e)}"
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"
