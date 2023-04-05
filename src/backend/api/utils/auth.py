from typing import Awaitable, Callable, Concatenate, ParamSpec
from argon2 import PasswordHasher
from starlette.requests import Request
from starlette.responses import Response
from api.data import handle
from api.utils.responses import ProblemResponse
from common.data.commands import GetUserIdFromSessionCommand, GetUserWithPermissionFromSessionCommand, IsValidSessionCommand
from common.data.models import Problem


pw_hasher = PasswordHasher()
P = ParamSpec('P')

def require_logged_in(handle_request: Callable[Concatenate[Request, P], Awaitable[Response]]):
    async def wrapper(request: Request, *args: P.args, **kwargs: P.kwargs):
        session_id = request.cookies.get("session", None)
        if session_id is None:
            raise Problem("Not logged in", status=401)

        user_id = await handle(GetUserIdFromSessionCommand(session_id))

        if user_id is not None:
            request.state.session_id = session_id
            request.state.user_id = user_id
            return await handle_request(request, *args, **kwargs)
        else:
            resp = ProblemResponse(Problem("Not logged in", status=401))
            resp.delete_cookie("session")
            return resp

    return wrapper

def require_permission(permission_name: str):
    def has_permission_decorator(handle_request: Callable[Concatenate[Request, P], Awaitable[Response]]):
        async def wrapper(request: Request, *args: P.args, **kwargs: P.kwargs):
            session_id = request.cookies.get("session", None)
            if session_id is None:
                raise Problem("Not logged in", status=401)
            
            user_id = await handle(GetUserWithPermissionFromSessionCommand(session_id, permission_name))

            if user_id is not None:
                request.state.session_id = session_id
                request.state.user_id = user_id
                return await handle_request(request, *args, **kwargs)
            
            if await handle(IsValidSessionCommand(session_id)):
                raise Problem("Insufficient permission", f"User does not have required permission \'{permission_name}\'", status=401)
            else:
                resp = ProblemResponse(Problem("Not logged in", status=401))
                resp.delete_cookie("session")
                return resp
        return wrapper
    return has_permission_decorator