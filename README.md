Sliver
======

An ['archival sliver'](https://inkdroid.org/2013/10/16/archival-sliver/), a bit like a ['data lifeboat'](https://www.flickr.org/programs/content-mobility/data-lifeboat/) for gathering small sets of pages from web archives or from the live web.

## Outline Workflow

The overall workflow is:

- Set up [pywb](https://github.com/webrecorder/pywb) as a proxy to talk to the live web, or web archives, leveraging it's support [extracting and recording items into WARCs with provenance info](https://pywb.readthedocs.io/en/latest/manual/configuring.html?highlight=remote#recording-mode).
- Generate a set of original URLs that we want to gather.
- Use browser-based screen-shotting tools to run through that list of URLs, going via the pywb proxy.
- Take the resulting WARC(s) and package them as WACZ with page detection and text extraction.
- Bundle the WACZ with a suitable index.html wrapper to allow playback from static resources. This could be running playback directly, or use the screenshots as a gallery and have a separate playback page or frame.


## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install hatch
```

## Generating a list of URLs

```sh
curl -o out.cdx -g "https://web.archive.org/cdx/search/cdx?url=example.com&collapse=urlkey&matchType=prefix&limit=10000&filter=statuscode:[23]..&showResumeKey=true"
```

Then extract the urls from the CDX. 

## Set pywb running

Run the proxy that will pull and record:

```sh
# Create a collection to record things into:
hatch run wb-manager init mementos
# Set the proxy running (it's on localhost:8080):
hatch run wayback --threads 12 > wayback.log 2>&1 &
```

The <./config.yaml> was pretty fiddly to get right for this!

## Run the screen shot capture

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

## WACZ Creation & Access

Made a WACZ

```sh
wacz create -o anjackson-net-2025-02-08.wacz -t -d collections/mementos/archive/MLB-20250208201638089003-EMEOIDCD.warc.gz
```

Copied it up so an S3 store (<https://european-alternatives.eu/category/object-storage-providers>, <https://www.s3compare.io/>) that I've made accessible over the web (<https://storj.dev/dcs/code/static-site-hosting>):

```sh
rclone copy slivers dr:slivers
```

Resulting in <https://slivers.anjackson.dev/anjackson-net-2025-02-08/>



## Example

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



Example WARC when original was accessed via the Memento API.

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