import random
from typing import Dict, List, Optional
from pydantic import BaseModel


class ProxyConfig(BaseModel):
    proxy_id: str
    server: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    country: str = "IN"
    is_healthy: bool = True


class ProxyManager:
    """
    Residential Proxy Manager & Rotation Pool (Layer F).
    """

    def __init__(self) -> None:
        self.proxies: List[ProxyConfig] = []

    def add_proxy(self, proxy: ProxyConfig) -> None:
        self.proxies.append(proxy)

    def get_proxy_for_site(self, site_name: str, country: str = "IN") -> Optional[ProxyConfig]:
        healthy = [p for p in self.proxies if p.is_healthy and p.country == country]
        if not healthy:
            healthy = [p for p in self.proxies if p.is_healthy]
        if not healthy:
            return None
        return random.choice(healthy)

    def mark_unhealthy(self, proxy_id: str) -> None:
        for p in self.proxies:
            if p.proxy_id == proxy_id:
                p.is_healthy = False
