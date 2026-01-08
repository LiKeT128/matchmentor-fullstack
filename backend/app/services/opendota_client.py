import aiohttp
import asyncio
from fastapi import HTTPException
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class OpenDotaClient:
    BASE_URL = "https://api.opendota.com/api"
    
    @staticmethod
    async def get_match(match_id: str) -> Dict[str, Any]:
        """Fetch match data from OpenDota API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{OpenDotaClient.BASE_URL}/matches/{match_id}"
                logger.info(f"Fetching from OpenDota: {url}")
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    logger.info(f"OpenDota Response Status: {resp.status}")
                    
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"✓ Got match data: {match_id}")
                        return data
                    elif resp.status == 404:
                        logger.warning(f"OpenDota returned 404 for {match_id}")
                        raise HTTPException(status_code=404, detail="Match not found in OpenDota")
                    elif resp.status == 429:
                        logger.warning(f"OpenDota Rate Limit (429) hit for {match_id}")
                        raise HTTPException(status_code=429, detail="OpenDota Rate Limit Exceeded")
                    else:
                        text = await resp.text()
                        logger.error(f"OpenDota Error {resp.status}: {text[:200]}")
                        raise HTTPException(status_code=502, detail=f"OpenDota API Error: {resp.status}")
        except asyncio.TimeoutError:
             logger.error("OpenDota request timed out")
             raise HTTPException(status_code=504, detail="OpenDota API timeout")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"OpenDota error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
