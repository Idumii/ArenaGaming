"""
Rate limiter pour respecter les limites de l'API Riot
"""
import asyncio
import time
from collections import deque

class RateLimiter:
    """Gestionnaire de limitation de taux pour l'API Riot"""
    
    def __init__(self, max_requests: int = 100, time_window: int = 120):
        """
        Args:
            max_requests: Nombre maximum de requêtes
            time_window: Fenêtre de temps en secondes
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self._lock = asyncio.Lock()
    
    async def wait(self):
        """Attendre si nécessaire avant de faire une requête"""
        async with self._lock:
            now = time.time()
            
            # Supprimer les requêtes trop anciennes
            while self.requests and self.requests[0] <= now - self.time_window:
                self.requests.popleft()
            
            # Si on a atteint la limite, attendre
            if len(self.requests) >= self.max_requests:
                sleep_time = self.time_window - (now - self.requests[0]) + 0.1
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    return await self.wait()  # Récursion pour vérifier à nouveau
            
            # Enregistrer cette requête
            self.requests.append(now)
