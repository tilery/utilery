import asyncio
import os
import uvloop
import sys

from gunicorn.workers.base import Worker


class Worker(Worker):

    def __init__(self, *args, **kw):  # pragma: no cover
        super().__init__(*args, **kw)

        self.servers = {}
        self.exit_code = 0

    def init_process(self):
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        # create new event_loop after fork
        asyncio.get_event_loop().close()

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        super().init_process()

    def run(self):
        self.loop.run_until_complete(self.wsgi.startup())
        self._runner = asyncio.ensure_future(self._run(), loop=self.loop)

        try:
            self.loop.run_until_complete(self._runner)
        finally:
            self.loop.close()

        sys.exit(self.exit_code)

    def make_handler(self, app):
        app.loop = self.loop
        return app

    async def close(self):
        if self.servers:
            servers = self.servers
            self.servers = None

            # stop accepting connections
            for server, handler in servers.items():
                self.log.info("Stopping server: %s, connections: %s",
                              self.pid, len(handler.connections))
                server.close()
                await server.wait_closed()

            # send on_shutdown event
            await self.wsgi.shutdown()

            # stop alive connections
            tasks = [
                handler.finish_connections(
                    timeout=self.cfg.graceful_timeout / 100 * 95)
                for handler in servers.values()]
            await asyncio.gather(*tasks, loop=self.loop)

            # cleanup application
            # yield from self.wsgi.cleanup()

    @asyncio.coroutine
    def _run(self):

        ctx = self._create_ssl_context(self.cfg) if self.cfg.is_ssl else None

        for sock in self.sockets:
            handler = self.make_handler(self.wsgi)
            srv = yield from asyncio.start_server(handler, sock=sock.sock,
                                                  ssl=ctx)
            self.servers[srv] = handler

        # If our parent changed then we shut down.
        pid = os.getpid()
        try:
            while self.alive or self.connections:
                self.notify()

                cnt = sum(handler.requests_count
                          for handler in self.servers.values())
                if self.cfg.max_requests and cnt > self.cfg.max_requests:
                    self.alive = False
                    self.log.info("Max requests, shutting down: %s", self)

                elif pid == os.getpid() and self.ppid != os.getppid():
                    self.alive = False
                    self.log.info("Parent changed, shutting down: %s", self)
                else:
                    yield from asyncio.sleep(1.0, loop=self.loop)

        except BaseException as e:
            print(e)
            pass

        yield from self.close()

    def handle_quit(self, sig, frame):
        self.alive = False

    def handle_abort(self, sig, frame):
        self.alive = False
        self.exit_code = 1
