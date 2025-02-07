Memento Lifeboat
================

An experimental ['data lifeboat'](https://www.flickr.org/programs/content-mobility/data-lifeboat/) for replicating pages from web archives.

The proposed workflow is:

- Use [pywb](https://github.com/webrecorder/pywb) as a proxy to talk to web archives, and leverage it's support [extracting and recording items into WARCs with provenance info](https://pywb.readthedocs.io/en/latest/manual/configuring.html?highlight=remote#recording-mode).
- Take a URL prefix as an argument and look up URLs under that prefix.
- Use browser-based screen-shotting tools to run through that list of URLs, via the proxy.
- Take the resulting WARC(s) and package them as WACZ.
- Bundle the WACZ with a suitable index.html wrapper to allow playback from static resources.




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