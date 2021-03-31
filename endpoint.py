from urllib.parse import urlparse, ParseResult
import json

import logging
logger = logging.getLogger('__main__.' + __name__)

# TODO move this function out of ssh_utils
from ssh_utils import get_server_private_ip


endpoint_to_port = {
    "server-nginx-quiche": "443",
    "server-nginx": "444",
    "server-caddy": "445", 
    "server-openlitespeed": "446"
}


def get_domain(url: str) -> str: 
    res: ParseResult = urlparse(url)
    return res.netloc


def get_path(url: str) -> str: 
    res: ParseResult = urlparse(url)
    return res.path


def get_external_json_dict(): 
    with open("external.json") as external_json:
        return json.load(external_json)


class Endpoint():
    url = ""
    domain = ""
    port = ""
    payload = "" 
    endpoint = ""
    on_server: bool = False
    def __init__(self, url :str, endpoint :str, payload :str): 
        if url: 
            self.url = url 
            parsed_url = urlparse(self.url)
            self.domain = parsed_url.netloc
            self.port = parsed_url.port 
            self.endpoint = f"URL-{self.url}"
            return 

        # If url was not specified, we require an endpoint AND a payload
        if not endpoint or not payload: 
            logger.error("When url is not specified, we need an endpoint and a payload.")
            raise Exception()

        self.endpoint = endpoint
        self.payload = payload

        # Special logic if on server VM vs public endpoint
        if endpoint in endpoint_to_port.keys():
            self.on_server = True
            self.domain = get_server_private_ip()
            self.port = endpoint_to_port[endpoint]
            self.url = f"{self.domain}:{self.port}/{self.payload}"
        else:
            # Use json file to get url for public endpoints
            # If the particular endpoint/payload is not available, throw an exception 
            # and handle it above (by silently not using this particular combo)
            try:  
                self.url = get_external_json_dict()[endpoint][payload]
            except Exception as e: 
                logger.exception("Need to specify an endpoint/payload combination that exists")
                raise e 

            parsed_url = urlparse(self.url)
            self.domain = parsed_url.netloc
            self.port = parsed_url.port 
    
    def get_url(self) -> str:
        return self.url

    def get_domain(self) -> str:
        return self.domain
    
    def is_on_server(self) -> bool: 
        return self.on_server
    
    def get_payload(self) -> str: 
        return self.payload

    def get_port(self) -> str: 
        return self.port

    def get_endpoint(self) -> str:
        return self.endpoint
