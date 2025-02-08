Memento Lifeboat
================

An experimental ['data lifeboat'](https://www.flickr.org/programs/content-mobility/data-lifeboat/) for replicating pages held in web archives.

The proposed workflow is:

- Use [pywb](https://github.com/webrecorder/pywb) as a proxy to talk to web archives, and leverage it's support [extracting and recording items into WARCs with provenance info](https://pywb.readthedocs.io/en/latest/manual/configuring.html?highlight=remote#recording-mode).
- Take a URL prefix as an argument and look up URLs under that prefix.
- Use browser-based screen-shotting tools to run through that list of URLs, via the proxy.
- Take the resulting WARC(s) and package them as WACZ.
- Bundle the WACZ with a suitable index.html wrapper to allow playback from static resources.

```sh
curl -o out.cdx -g "https://web.archive.org/cdx/search/cdx?url=vawnet.org&collapse=urlkey&matchType=prefix&limit=10000&filter=statuscode:[23]..&showResumeKey=true"
```

Then extract the urls from the CDX. Use it to populate a `shots.yml` file.

Set up shot-scraper

```sh
hatch run shot-scraper install -b chromium
```

Run the proxy that will pull and record:

```sh
hatch run wayback > wayback.log 2>&1 &
```

```sh
hatch run shot-scraper multi -b chromium --browser-arg '--ignore-certificate-errors --proxy-server=http://localhost:8080' shots.yml
```

Ran this against about 80 Twitter URLs. A hanfful of errors, presumably due to rate limiting by the source archive, but it's difficult to tell. Generally reasonable results, but long waits needed between pages to try to ensure minimal blocking.

- Using the `multi` mode and config is cumbersome as you need to repeat a lot of config.
- It will auto-generate names for the screenshots, but then seems to repeat screenshots and give them new names with `.1` etc. Which kinda defeats the purpose.
- Having to set all the browser options etc. at the command-line is obviously rather brittle.
- No video, presumably because Chromium?

So, it would make sense to wrap this all up as a new command that would launch the proxy, run the shots, and gather the results. e.g.

```sh
$ memento-lifeboat collection-urls.txt
```

With this generating a `collection-urls.wacz` by default.


```sh
rclone copy memento-lifeboats dr:memento-lifeboats
```


## Extraction

https://pywb.readthedocs.io/en/latest/manual/warcserver.html#custom-warcserver-deployments


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