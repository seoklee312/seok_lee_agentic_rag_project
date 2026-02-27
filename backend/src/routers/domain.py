"""
Domain API Router
Endpoints for domain switching and interaction
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/domain", tags=["domain"])


class DomainSwitchRequest(BaseModel):
    """Request to switch domain"""
    domain: str


class DomainQueryRequest(BaseModel):
    """Request to query a domain"""
    query: str
    domain: Optional[str] = None


class ToolExecuteRequest(BaseModel):
    """Request to execute a domain tool"""
    tool_name: str
    domain: Optional[str] = None
    parameters: Dict[str, Any] = {}


@router.get("/list")
async def list_domains(request: Request):
    """List available domains"""
    domain_manager = request.app.state.domain_manager
    domains = domain_manager.list_available_domains()
    
    return {
        "domains": domains,
        "active": domain_manager.get_active_domain().get_name() if domain_manager.get_active_domain() else None
    }


@router.post("/switch")
async def switch_domain(req: DomainSwitchRequest, request: Request):
    """Switch to a different domain"""
    domain_manager = request.app.state.domain_manager
    
    try:
        domain = domain_manager.switch_domain(req.domain)
        return {
            "success": True,
            "domain": domain.get_name(),
            "system_prompt": domain.get_system_prompt()[:200] + "...",
            "tools": domain.get_tools().list_tools()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/active")
async def get_active_domain(request: Request):
    """Get currently active domain"""
    domain_manager = request.app.state.domain_manager
    domain = domain_manager.get_active_domain()
    
    if not domain:
        raise HTTPException(status_code=404, detail="No active domain")
    
    return {
        "domain": domain.get_name(),
        "system_prompt": domain.get_system_prompt()[:200] + "...",
        "tools": domain.get_tools().list_tools(),
        "retrieval_config": domain.get_retrieval_config()
    }


@router.post("/query")
async def query_domain(req: DomainQueryRequest, request: Request):
    """Query using active or specified domain"""
    domain_manager = request.app.state.domain_manager
    grok_llm = request.app.state.grok_llm
    
    # Get domain
    if req.domain:
        domain = domain_manager.switch_domain(req.domain)
    else:
        domain = domain_manager.get_active_domain()
        if not domain:
            raise HTTPException(status_code=400, detail="No active domain. Specify domain or switch first.")
    
    # Process query
    processed_query = domain.preprocess_query(req.query)
    
    messages = [
        {"role": "system", "content": domain.get_system_prompt()},
        {"role": "user", "content": processed_query}
    ]
    
    try:
        response = await grok_llm.generate(messages, max_tokens=500)
        final_response = domain.postprocess_response(response['content'])
        
        return {
            "domain": domain.get_name(),
            "query": req.query,
            "response": final_response,
            "model": response.get('model'),
            "usage": response.get('usage')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/tool/execute")
async def execute_tool(req: ToolExecuteRequest, request: Request):
    """Execute a domain-specific tool"""
    domain_manager = request.app.state.domain_manager
    
    # Get domain
    if req.domain:
        domain = domain_manager.switch_domain(req.domain)
    else:
        domain = domain_manager.get_active_domain()
        if not domain:
            raise HTTPException(status_code=400, detail="No active domain")
    
    # Execute tool
    try:
        result = await domain.get_tools().execute(req.tool_name, **req.parameters)
        return {
            "domain": domain.get_name(),
            "tool": req.tool_name,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Tool execution failed: {str(e)}")
