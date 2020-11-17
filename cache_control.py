# Contains functions to insert/remove caching in server config
def remove_server_caching(file_name, line_num):
    """ Insert lines into server conf to disable caching
    """

    f = open(file_name, 'r')
    lines=f.readlines()
    f.close()

    text = ["        location / {",
    "            root /usr/local/nginx/html;",
    "            index index.html",
    "            # kill cache",
    "            add_header Cache-Control 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0';",
    "            if_modified_since off;",
    "            expires off;",
    "            etag off;",
    "        }"]
    for line in text[::-1]:
        lines.insert(line_num, line+"\n")

    f = open(file_name, "w")
    lines = "".join(lines)
    f.write(lines)
    f.close()

def add_server_caching(file_name, start_index, num_lines):
    """ Delete lines from server conf to enable caching
    """
    f = open(file_name, 'r')
    lines=f.readlines()
    f.close()

    for _ in range(num_lines):
        del lines[start_index]

    f = open(file_name, "w")
    lines = "".join(lines)
    f.write(lines)
    f.close()

