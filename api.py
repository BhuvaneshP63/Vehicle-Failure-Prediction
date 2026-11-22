import json
import os
import asyncio

import tornado.web
from src.operations import ingest, Conflict


class Reading(tornado.web.RequestHandler):
    async def post(self):
        try:
            result = await asyncio.to_thread(ingest, json.loads(self.request.body))
        except (ValueError, UnicodeError) as exc:
            self.set_status(409 if isinstance(exc, Conflict) else 400)
            self.finish({"error": str(exc)})
            return
        self.set_status(200 if result["duplicate"] else 201)
        self.finish(result)


async def main():
    app = tornado.web.Application([(r"/v1/readings", Reading)])
    app.listen(8765, address=os.getenv("VFP_BIND", "127.0.0.1"), max_body_size=65536)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
