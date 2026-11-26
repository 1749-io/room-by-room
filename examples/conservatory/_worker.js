// Pages can return the entire static MP4 even when the browser requests a range.
// This route serves the reviewed 5.5 MB film; other assets use static Pages.
export default {
  async fetch(request, env) {
    if (new URL(request.url).pathname !== "/orchard/walkthrough-v3.mp4") {
      return env.ASSETS.fetch(request);
    }
    const asset = await env.ASSETS.fetch(request);
    if (asset.status !== 200) return asset;

    const headers = new Headers(asset.headers);
    headers.set("Accept-Ranges", "bytes");
    const full = () => new Response(asset.body, {status: 200, headers});
    const range = request.headers.get("Range");
    if (request.method !== "GET" || !range) return full();
    const validator = request.headers.get("If-Range");
    if (validator && validator !== headers.get("etag") && validator !== headers.get("last-modified")) {
      return full();
    }
    const match = /^bytes=(\d*)-(\d*)$/i.exec(range.trim());
    if (!match || (!match[1] && !match[2])) return full();

    const bytes = await asset.arrayBuffer();
    const size = bytes.byteLength;
    const start = match[1] ? Number(match[1]) : Math.max(0, size - Number(match[2]));
    const end = match[1] && match[2] ? Math.min(Number(match[2]), size - 1) : size - 1;
    headers.delete("content-encoding");
    if (start >= size || start > end) {
      headers.set("Content-Range", `bytes */${size}`);
      headers.set("Content-Length", "0");
      return new Response(null, {status: 416, headers});
    }
    headers.set("Content-Range", `bytes ${start}-${end}/${size}`);
    headers.set("Content-Length", String(end - start + 1));
    return new Response(bytes.slice(start, end + 1), {status: 206, headers});
  }
};
