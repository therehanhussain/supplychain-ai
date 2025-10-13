import asyncio
import logging
import os
import sys

import ray

from agentsociety.cityagent import default
from agentsociety.configs import Config, load_config_from_file
from agentsociety.simulation import AgentSociety

async def main():
    ray.init(logging_level=logging.INFO)
    config = load_config_from_file(
        filepath="config.yaml",
        config_type=Config,
    )
    config = default(config) 
    agentsociety = AgentSociety(config)
    await agentsociety.init() 
    await agentsociety.run()
    await agentsociety.close()
    ray.shutdown()
    # 1.问价 添加 base_price 基底
    # 2.相关订单加topic
    # 3.先让大模型接收超额订单，可以变负数，后续增加产能调整模块，可以不立马交付货物


if __name__ == "__main__":
    asyncio.run(main())
