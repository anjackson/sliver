import os
import click
import logging
import urllib.parse
import urllib.request
from pywb.apps.cli import WaybackCli
from pywb.utils.loaders import load_yaml_config
from shot_scraper.cli import multi

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(levelname)s - %(message)s'
)

class EmbeddedWaybackCli(WaybackCli):
    """CLI class for starting the pywb's implementation of the Wayback Machine in an embedded mode"""
    extra_config = load_yaml_config('./config.yaml')

    def load(self):
        return super(EmbeddedWaybackCli, self).load()
        
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


# Shared options
# How to handle.... http://index.commoncrawl.org/collinfo.json ??
source_option = click.option('--source', type=click.Choice(['live', 'ia', 'cc']), default="ia", help='Source of the data', show_default=True)

@click.group()
def cli():
    pass

@click.command()
@click.argument('url')
@source_option
def lookup(url, source):
    """URL to use as a prefix for the lookup query"""
    logging.info(f"Lookup URLs starting with: {url}")
    matchType = "prefix"
    filter = "statuscode:[23].."
    if source == "cc-2025-05" or source == "cc":
        URL = "http://index.commoncrawl.org/CC-MAIN-2025-05-index"
        matchType = "host"
        logging.warning("Common Crawl index is used, which only supports host-level prefix searches. This may take a while...")
        filter = ""
    elif source == "ia":
        URL = "https://web.archive.org/cdx/search/cdx"
    else:
        raise ValueError("Unknown source")
    logging.info(f"Using source: {source}")

    params = {
        "url": url,
        "collapse": "urlkey",
        "matchType": matchType,
        "limit": 10000,
        "filter": filter,
        "showResumeKey": True
    }

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
                    click.echo(cdx)
            elif resumeKey is None:
                resumeKey = line.decode('utf-8').strip()

    if resumeKey is not None:
        logging.warning(f"Use the following resume key for the next query: {resumeKey}")

@click.command()
@source_option
def fetch(source):
    logging.info("Fetch command executed")
    # Set up the required folders for this to work:
    os.makedirs('collections/mementos/index')
    os.makedirs('collections/mementos/archives')
    # Start PyWB with the appropriate source configuration:
    embedded = EmbeddedWaybackCli(args=['-t', '16'])
    embedded.run()
    logging.info("PyWB started...")
    # Loop through the supplied URLs and check if we need to fetch them:
    # Run the screen shot code on the URL, with the right proxy settings:
    multi( [ '-b', 'chromium', '--browser-arg', '--ignore-certificate-errors', '--browser-arg', '--proxy-server=http://localhost:8080', 'tests/shots.yml'] )
    # Shutdown PyWB:
    embedded.ge.stop()
    logging.info("PyWB stopped")

    # Tidy up the output:


cli.add_command(lookup)
cli.add_command(fetch)

if __name__ == "__main__":
    cli()
 