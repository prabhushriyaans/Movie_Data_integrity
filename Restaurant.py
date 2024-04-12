from uagents import Agent, Context
from uagents.setup import fund_agent_if_low
from typing import List
from uagents import Context, Model, Protocol,Bureau


class TableStatus(Model):
    seats: int
    time_start: int
    time_end: int
 
class QueryTableRequest(Model):
    guests: int
    time_start: int
    duration: int
 
class QueryTableResponse(Model):
    tables: List[int]
 
class GetTotalQueries(Model):
    pass
 
class TotalQueries(Model):
    total_queries: int
query_proto = Protocol()
 
@query_proto.on_message(model=QueryTableRequest, replies=QueryTableResponse)
async def handle_query_request(ctx: Context, sender: str, msg: QueryTableRequest):
    tables = {
        int(num): TableStatus(**status)
        for (
            num,
            status,
        ) in ctx.storage._data.items()
        if isinstance(num, int)
    }
    available_tables = []
    for number, status in tables.items():
        if (
            status.seats >= msg.guests
            and status.time_start <= msg.time_start
            and status.time_end >= msg.time_start + msg.duration
        ):
            available_tables.append(int(number))
    ctx.logger.info(f"Query: {msg}. Available tables: {available_tables}.")
    await ctx.send(sender, QueryTableResponse(tables=available_tables))
    total_queries = int(ctx.storage.get("total_queries") or 0)
    ctx.storage.set("total_queries", total_queries + 1)
 
@query_proto.on_query(model=GetTotalQueries, replies=TotalQueries)
async def handle_get_total_queries(ctx: Context, sender: str, _msg: GetTotalQueries):
    total_queries = int(ctx.storage.get("total_queries") or 0)
    await ctx.send(sender, TotalQueries(total_queries=total_queries))
# from uagents import Context, Model, Protocol
# from .query import TableStatus
 
class BookTableRequest(Model):
    table_number: int
    time_start: int
    duration: int
 
class BookTableResponse(Model):
    success: bool
 
book_proto = Protocol()
@book_proto.on_message(model=BookTableRequest, replies=BookTableResponse)
async def handle_book_request(ctx: Context, sender: str, msg: BookTableRequest):
    tables = {
        int(num): TableStatus(**status)
        for (
            num,
            status,
        ) in ctx.storage._data.items()
        if isinstance(num, int)
    }
    table = tables[msg.table_number]
    if (
        table.time_start <= msg.time_start
        and table.time_end >= msg.time_start + msg.duration
    ):
        success = True
        table.time_start = msg.time_start + msg.duration
        ctx.storage.set(msg.table_number, table.dict())
    else:
        success = False
    # send the response
    await ctx.send(sender, BookTableResponse(success=success))

restaurant = Agent(
    name="restaurant",
    port=8001,
    seed="restaurant secret phrase",
    endpoint=["http://127.0.0.1:8001/submit"],
)
 
fund_agent_if_low(restaurant.wallet.address())
 
# build the restaurant agent from stock protocols
restaurant.include(query_proto)
restaurant.include(book_proto)
TABLES = {
    1: TableStatus(seats=2, time_start=16, time_end=22),
    2: TableStatus(seats=4, time_start=19, time_end=21),
    3: TableStatus(seats=4, time_start=17, time_end=19),
}
 
# set the table availability information in the restaurant protocols
for (number, status) in TABLES.items():
    restaurant._storage.set(number, status.dict())
 
if __name__ == "__main__":
    restaurant.run()

from uagents import Agent, Context
from uagents.setup import fund_agent_if_low
 
RESTAURANT_ADDRESS = "agent1qw50wcs4nd723ya9j8mwxglnhs2kzzhh0et0yl34vr75hualsyqvqdzl990"
 
user = Agent(
    name="user",
    port=8000,
    seed="user secret phrase",
    endpoint=["http://127.0.0.1:8000/submit"],
)
 
fund_agent_if_low(user.wallet.address())
 
table_query = QueryTableRequest(
    guests=3,
    time_start=19,
    duration=2,
)
 
# This on_interval agent function performs a request on a defined period
@user.on_interval(period=3.0, messages=QueryTableRequest)
async def interval(ctx: Context):
    completed = ctx.storage.get("completed")
 
    if not completed:
        await ctx.send(RESTAURANT_ADDRESS, table_query)
 
@user.on_message(QueryTableResponse, replies={BookTableRequest})
async def handle_query_response(ctx: Context, sender: str, msg: QueryTableResponse):
    if len(msg.tables) > 0:
        ctx.logger.info("There is a free table, attempting to book one now")
 
        table_number = msg.tables[0]
 
        request = BookTableRequest(
            table_number=table_number,
            time_start=table_query.time_start,
            duration=table_query.duration,
        )
 
        await ctx.send(sender, request)
 
    else:
 
        ctx.logger.info("No free tables - nothing more to do")
        ctx.storage.set("completed", True)
 
@user.on_message(BookTableResponse, replies=set())
async def handle_book_response(ctx: Context, _sender: str, msg: BookTableResponse):
    if msg.success:
        ctx.logger.info("Table reservation was successful")
 
    else:
        ctx.logger.info("Table reservation was UNSUCCESSFUL")
 
    ctx.storage.set("completed", True)
 
if __name__ == "__main__":
    user.run()

bureau= Bureau()
bureau.add(restaurant)
bureau.add(user)

if __name__=="__main__":
    bureau.run()
    