import os
import time
import yaml
import click
import logging
import tempfile
import urllib.parse
import urllib.request
from pywb.apps.cli import WaybackCli
from shot_scraper.cli import multi
from shot_scraper.utils import filename_for_url

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(levelname)s - %(message)s'
)

class EmbeddedWaybackCli(WaybackCli):
    """CLI class for starting the pywb's implementation of the Wayback Machine in an embedded mode"""
   
    # Define the sources we can use: 
    sources = {
        'live': '$live', 
        'ia': 'memento+https://web.archive.org/web/', 
        'ia_cdx': 'cdx+https://web.archive.org/cdx /web'
    }
    
    def _extend_parser(self, parser):
        # Collect the superclass parser extensions:    
        super(EmbeddedWaybackCli, self)._extend_parser(parser)
        
        # Add the source option:
        parser.add_argument(
            '--source', 
            choices=self.sources.keys(), 
            default='live',
            help='Source of the data')
        # Add the timestamp option:
        parser.add_argument(
            '--timestamp', default='19950101000000',
            help="Target timestamp to use for the proxy requests")

    def load(self):
        # Set up the extra_config:
        self.extra_config = {
            'collections': {
                'ia': 'memento+https://web.archive.org/web/',
                'ia_cdx': 'cdx+https://web.archive.org/cdx /web',
                'live': { 'index': '$live'},
                'stack': {
                    'sequence': []
                }
            }, 
            'recorder': {
                'source_coll': 'stack', 
                'source_filter': 'source', 
                'filename_template': 'SLIVER-{timestamp}-{random}.warc.gz'
            }, 
            'proxy': {
                'coll': 'mementos', 
                'recording': True, 
                'default_timestamp': self.r.timestamp
            }, 
            'autoindex': 10, 
            'enable_auto_fetch': True,
            'enable_wombat': True
        }
        
        # Stacking not required for live web fetches:
        if self.r.source == 'live':
            self.extra_config['collections']['stack']['sequence']= [{'name': 'source', 'index': '$live'}]
        else:
            # Stack the sources so we can fetch from the local and remote archive:
            self.extra_config['collections']['stack']['sequence'] = [
                {
                    'archive_paths': './collections/mementos/archive/',
                    'index_paths': './collections/mementos/indexes',
                    'name': 'mementos'
                },
                {
                    'index': 'memento+https://web.archive.org/web/',
                    'name': 'source'
                }]

        # Do the superclass setup:
        app = super(EmbeddedWaybackCli, self).load()        
        return app
        
    # Override this method, so it runs in the background.
    def run_gevent(self):
        """Created the server that runs the application supplied a subclass"""
        from pywb.utils.geventserver import GeventServer, RequestURIWSGIHandler
        logging.info('Starting Embedded Gevent Server on ' + str(self.r.port))
        self.ge = GeventServer(self.application,
                          port=self.r.port,
                          hostname=self.r.bind,
                          handler_class=RequestURIWSGIHandler,
                          direct=False)


@click.group()
def cli():
    pass

@click.command()
@click.argument("url")
@click.option('-s', '--source', type=click.Choice(['ia', 'cc']), default="ia", help="Source index to query for known URLs. Internet Archive Wayback Machine is 'ia'. Common Crawl is 'cc' (under development!).", show_default=True)
@click.option('-L', '--limit', type=int, default=10_000, help="Limit the number of results returned.", show_default=True)
@click.option('-f', '--filter', type=str, default="statuscode:[23]..", help="Filter to apply to the results. Default value only returns HTTP 2XX or 3XX records.", show_default=True)
@click.option('-r', '--resume-key', type=str, help="Resume key to use for the query.")
@click.option('-o', '--output', type=click.File('w'), default="-", help="Output file to write the results to. Default writes to <STDOUT>.", show_default=True)
def lookup(url, source, limit, filter, resume_key, output):
    """
    Looks up URLs based on a URL prefix.

    Can run queries against a web archive to find URLs that match a given prefix. Outputs the results in CDX format to <STDOUT>.
    
    URL: URL to use as a prefix for the lookup query."""
    logging.info(f"Lookup URLs starting with: {url}")
    matchType = "prefix"
    if source == "cc-2025-05" or source == "cc":
        URL = "http://index.commoncrawl.org/CC-MAIN-2025-05-index"
        matchType = "host"
        logging.warning("Common Crawl index is used, which only supports host-level prefix searches. This may take a while...")
        filter = ""
    elif source == "ia":
        URL = "https://web.archive.org/cdx/search/cdx"
    else:
        raise ValueError("Unknown source!")
    logging.info(f"Using source: {source}")

    params = {
        "url": url,
        "collapse": "urlkey",
        "matchType": matchType,
        "limit": limit,
        "filter": filter,
        "showResumeKey": True
    }
    if resume_key is not None:
        params["resumeKey"] = resume_key

    # Build the query string:
    query_string = urllib.parse.urlencode(params)
    full_url = f"{URL}?{query_string}"
    logging.info(f"Full URL: {full_url}")
    resumeKey = None
    ended = False
    with urllib.request.urlopen(full_url) as response:
        for line in response:
            if not ended:
                cdx = line.decode('utf-8').strip()
                if cdx == "":
                    ended = True
                else:
                    # FIXME filter our lines that are not under the supplied path prefix (i.e. cope with host-level matching of the CC indexes)
                    click.echo(cdx, output)
            elif resumeKey is None:
                resumeKey = line.decode('utf-8').strip()

    if resumeKey is not None:
        logging.warning(f"Use the following resume key for the next query: {resumeKey}")

@click.command()
@click.argument("url-file", type=click.File('r'))
@click.option('-s', '--source', type=click.Choice(['live', 'ia']), default="live", help='Source to gather web resources from.', show_default=True)
@click.option('-t', '--timestamp', type=str, default="19950101000000", help="Target timestamp to use when gathering records from web archives, 14-digit 'YYYYMMDDHHMMSS' format.", show_default=True)
@click.option('-W', '--wait', type=int, default=15_000, help="Time to wait before taking a screenshot, in milliseconds.", show_default=True)
@click.option('-w', '--width', type=int, default=800, help="Width of the browser window.", show_default=True)
@click.option('-h', '--height', type=int, default=800, help="Height of the browser window.", show_default=True)
@click.option('-p', '--padding', type=int, help="Override default browser window padding. Use 0 for no padding.")
#@click.option('-b', '--browser', type=str, help="Browser to use for the screenshots. If unspecified, uses shot-scraper default.")
def fetch(url_file, source, timestamp, wait, width, height, padding):
    """
    Fetches archives and screenshots a set of URLs.
    
    URL_FILE: a plain test file with one URL per line.
    """
    logging.info("Fetch command executed")
    # Set up the required folders for this to work:
    os.makedirs('collections/mementos/indexes', exist_ok=True)
    os.makedirs('collections/mementos/archive', exist_ok=True)
    os.makedirs('collections/mementos/screenshots', exist_ok=True)
    # Start PyWB with the appropriate source configuration:
    embedded = EmbeddedWaybackCli(args=['--source', source])
    embedded.run()
    logging.info("PyWB started...")
    # Give PyWB a little moment to start up:
    time.sleep(3)

    # Loop through the supplied URLs and check if we need to fetch them, building up a config file:
    shots = []
    for url in url_file:
        url = url.strip()
        if url and not url.startswith("#"):
            shot = {
                'url': url,
                'output': f'collections/mementos/screenshots/{filename_for_url(url)}',
                'wait': wait,
                'width':  width,
                'height': height
            }
            # TODO: make some of the above optional config passed in as arguments.
            if padding:
                shot['padding'] = padding
            # And add it:
            shots.append(shot)

    # Run the screen shot code on the URL, with the right proxy settings:
    # Can add ['-b', 'chrome'] to force a particular browser to be used.
    # e.g. hatch run playwright install chrome

    # Set the proxy timestamp:
    # TODO: Need to run each screenshot separately so we can restart with a new timestamp in the proxy.
    # Might also have to note that because of the way it works, gathering multiple timestamps will probably not do what you want.
    embedded.application.proxy_default_timestamp = timestamp

    with tempfile.NamedTemporaryFile(mode="w", prefix="shots-", suffix=".yaml", delete=False) as fp:
            # Write the shots to a file that will get removed after the screenshot code has run:
            yaml.dump(shots, fp)
            fp.close()

            # Run the screenshot code with the shots file:
            multi( [ '--browser-arg', '--ignore-certificate-errors', '--browser-arg', '--proxy-server=http://localhost:8080', fp.name] )
    
    # Shutdown PyWB:
    embedded.ge.stop()
    logging.info("PyWB stopped.")



cli.add_command(lookup)
cli.add_command(fetch)

if __name__ == "__main__":
    cli()
 