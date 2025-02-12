Sliver
======

An ['archival sliver'](https://inkdroid.org/2013/10/16/archival-sliver/), a bit like a ['data lifeboat'](https://www.flickr.org/programs/content-mobility/data-lifeboat/) for making web archives of small sets of pages. Uses [`shot-scraper`](https://shot-scraper.datasette.io/) to drive a web browser that generates screenshots of your URLs, but runs it through a [`pywb`](https://github.com/webrecorder/pywb) web proxy so it can produce a high quality archival version of what you download.

As well as archiving live web pages, this tools can leverage pywb's support for [neatly extracting URLs from other web archives and recording items with all the appropriate provenance information](https://pywb.readthedocs.io/en/latest/manual/configuring.html?highlight=remote#recording-mode). This means it can work like [hartator/wayback-machine-downloader](https://github.com/hartator/wayback-machine-downloader) but retain the additional information that the WARC web archiving format supports (see 'Why WARC?' below).

Your use of this tool should take into account your legal context and the terms of use of the web sites and web archives you are working with.

### Other Tools

For very high-quality web archiving, you should take a look at [ArchiveWeb.page](https://archiveweb.page/) (for manual crawling via a browser extension) and [Browsertrix](https://webrecorder.net/browsertrix/) (for larger-scale high-quality crawling, running on Kubernetes).

You can find out more about web archives and web archiving tools and services via [iipc/awesome-web-archiving: An Awesome List for getting started with web archiving](https://github.com/iipc/awesome-web-archiving).

### Why WARC?

Web archives use the [WARC](https://en.wikipedia.org/wiki/WARC_(file_format)) format rather than just mirror the files from a website on disk. This is primarily because the WARC format also stores all the HTTP response headers, like `Content-Type`, that you need for playback to work reliably. They also store lots of contextual and provenance information.

## Usage

### Setup

Set up a Python environment with `sliver` installed. This setup is based on using [`uv`](https://docs.astral.sh/uv/) and assumes you already have that installed.

```sh
uv tool install https://github.com/anjackson/sliver.git
```

You should now be able to run e.g.

```sh
uvx sliver --help
```

Now create a directory to work in, to keep the archival files together as you work.

```sh
mkdir my-collection
cd my-collection
```

### Create a list of URLs

Create a list of URLs you want to archive.

For crawls from web archives, you can use the `sliver lookup` command for this.

### Fetch the URLs

Run `sliver fetch` to run the screen-shotting process via the archiving proxy.

```sh
uvx sliver fetch urls.txt
```
(running on port 8080)

During this process, the archives and screenshots are collected in subfolders of a local directory called  `./collections/mementos/`


```sh
uvx sliver fetch --source ia --timestamp 20050101000000 urls.txt
```

The archive gets updated...

Check the screenshots you have produced to see if they are good enough. Re-run `sliver fetch` if needed.

### Use the proxy to add to your archive

__TBD__ If you want to drive the crawl yourself, using `sliver proxy` to run the web proxy and configure your browser to use it.

### Package the results

__TBD__ Run `sliver package` to package the WARCs and screenshots etc. into a [WACZ web archive zip package](https://specs.webrecorder.net/wacz/latest/).


```sh
uvx sliver package
```

### Usage

Check the final package works using [ReplayWeb.page](https://replayweb.page/).

If you want, upload the package to a static site as per [Embedding ReplayWeb.page](https://replayweb.page/docs/embedding/)

Upload example


## Initial Prototype Notes

The following notes describe how the initial attempt at patching things together worked. These steps are being moved into the code.

### Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install hatch
```

### Generating a list of URLs

```sh
curl -o out.cdx -g "https://web.archive.org/cdx/search/cdx?url=example.com&collapse=urlkey&matchType=prefix&limit=10000&filter=statuscode:[23]..&showResumeKey=true"
```

Then extract the urls from the CDX. 

### Set pywb running

Run the proxy that will pull and record:

```sh
# Create a collection to record things into:
hatch run wb-manager init mementos
# Set the proxy running (it's on localhost:8080):
hatch run wayback --threads 12 > wayback.log 2>&1 &
```

The <./config.yaml> was pretty fiddly to get right for this!

### Run the screen shot capture

Set up shot-scraper

```sh
hatch run shot-scraper install -b chromium
```

Take the URLs from the CDX file and populate a `shots.yml` file.

Then run `shot-scraper` with the right settings, so everything goes via the proxy:

```sh
hatch run shot-scraper multi -b chromium --browser-arg '--ignore-certificate-errors' --browser-arg '--proxy-server=http://localhost:8080' --timeout 65000 shots.yml
```

Ran this against about 80 Twitter URLs. A handful of errors, presumably due to rate limiting by the source archive, but it's difficult to tell. Generally reasonable results, but long waits (30s+) needed between pages to try to ensure minimal blocking.

- Using the `multi` mode and config is cumbersome as you need to repeat a lot of config.
- It will auto-generate names for the screenshots, but then seems to repeat screenshots and give them new names with `.1` etc. Which kinda defeats the purpose.
- Having to set all the browser options etc. at the command-line is obviously rather brittle.
- No video, presumably because Chromium?
- This only gets one instance per URL, the earliest one.

So, it would make sense to wrap this all up as a new command that would launch the proxy, run the shots, and gather the results. e.g.

```sh
$ sliver collection-urls.txt
```

Perhaps using <https://pywb.readthedocs.io/en/latest/manual/warcserver.html#custom-warcserver-deployments> rather than a config file so it's all in code. Or maybe `export PYWB_CONFIG_FILE=...../config.yaml`... yes that works and is easier to manage.

With this generating a `collection-urls.wacz` by default.

### WACZ Creation & Access

Made a WACZ

```sh
wacz create -o anjackson-net-2025-02-08.wacz -t -d collections/mementos/archive/MLB-20250208201638089003-EMEOIDCD.warc.gz
```

Copied it up so an S3 store (<https://european-alternatives.eu/category/object-storage-providers>, <https://www.s3compare.io/>) that I've made accessible over the web (<https://storj.dev/dcs/code/static-site-hosting>):

```sh
rclone copy -v slivers dr:slivers # or sync???
uplink share --dns slivers.anjackson.dev sj://slivers --not-after=none
```

Resulting in <https://slivers.anjackson.dev/anjackson-net-2025-02-08/>


### Example Command Sequence

```sh
hatch run wb-manager init mementos
export PYWB_CONFIG_FILE=../../config.yaml 
hatch run wayback > wayback.log 2>&1 &
hatch run shot-scraper multi -b chromium --browser-arg '--ignore-certificate-errors' --browser-arg '--proxy-server=http://localhost:8080' shots.yaml 
hatch run wacz create -o example-com.wacz -t -d collections/mementos/archive/SLIVER-20250208210345321032-57CQFSUN.warc.gz
 ```
Then test in <https://replayweb.page/>

Then clean up and upload

## Extracted WARC Records

Example WARC when pulled from a source archive via the [Memento API](https://timetravel.mementoweb.org/guide/api/).

```warc
WARC/1.0
WARC-Type: response
WARC-Record-ID: <urn:uuid:e082c042-e56d-11ef-bbba-d982d0cb2308>
WARC-Target-URI: https://example.com/
WARC-Date: 2025-02-07T00:00:31Z
WARC-Source-URI: https://web.archive.org/web/20250207000031id_/https://example.com/
WARC-Creation-Date: 2025-02-07T16:09:15Z
WARC-IP-Address: 207.241.237.3
Content-Type: application/http; msgtype=response
Content-Length: 2239
WARC-Payload-Digest: sha1:YXWQ7LLPPIZ7CVO6DVQ4U3Y2IO5M42AG
WARC-Block-Digest: sha1:HBKFWTAU4TPQWD5CNKVIJVW2CANQUTRN

```