import time

def rendertime(get_response):
    def middleware(request):
        t1 = time.time()
        response = get_response(request)
        t2 = time.time()
        duration = t2 - t1
        duration = round(duration * 1000, 3)
        response.content = response.content.replace(b"PUTTHERENDERTIMEHERE", bytes(str(duration), "utf-8"), 1)
        return response
    return middleware