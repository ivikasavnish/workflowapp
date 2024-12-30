import json
from dataclasses import asdict, dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

@dataclass
class NodeConfig:
    """Configuration for a node that can be serialized"""
    node_id: str
    node_type: str
    next_nodes: List[str]
    properties: Dict[str, Any]  # Store node-specific properties
    metadata: Optional[Dict] = None

class NodeSerializer:
    """Handles serialization and deserialization of nodes"""
    
    @staticmethod
    def serialize_network(network: 'NodeNetwork') -> dict:
        """Convert entire network to serializable format"""
        nodes_config = {}
        
        for node_id, node in network.nodes.items():
            nodes_config[node_id] = NodeSerializer.serialize_node(node)
        
        return {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "nodes": nodes_config
        }
    
    @staticmethod
    def serialize_node(node: 'BaseNode') -> NodeConfig:
        """Convert a node to serializable format"""
        properties = {}
        
        # Serialize based on node type
        if isinstance(node, WorkNode):
            properties["work_type"] = node.work_func.__name__
        elif isinstance(node, RouterNode):
            # Convert routing rules to serializable format
            properties["routing_rules"] = {
                f"rule_{i}": target_node
                for i, (_, target_node) in enumerate(node.routing_rules.items())
            }
        elif isinstance(node, HTTPNode):
            properties["endpoint"] = node.endpoint
        
        return NodeConfig(
            node_id=node.node_id,
            node_type=node.__class__.__name__,
            next_nodes=node.next_nodes if hasattr(node, 'next_nodes') else [],
            properties=properties,
            metadata={
                "created_at": datetime.now().isoformat(),
                "status": node.status.value
            }
        )
    
    @staticmethod
    def save_to_file(network: 'NodeNetwork', filepath: str):
        """Save network configuration to JSON file"""
        config = NodeSerializer.serialize_network(network)
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
    
    @staticmethod
    def load_from_file(filepath: str) -> dict:
        """Load network configuration from JSON file"""
        with open(filepath, 'r') as f:
            return json.load(f)

class NodeFactory:
    """Creates nodes from configuration"""
    
    @staticmethod
    def create_network_from_config(config: dict) -> 'NodeNetwork':
        """Create a new network from configuration"""
        network = NodeNetwork()
        
        # First pass: Create all nodes
        for node_id, node_config in config['nodes'].items():
            node = NodeFactory.create_node(node_config)
            network.add_node(node)
        
        # Second pass: Connect nodes
        for node_id, node_config in config['nodes'].items():
            if node_config.next_nodes:
                for next_node in node_config.next_nodes:
                    network.connect_nodes(node_id, next_node)
        
        return network
    
    @staticmethod
    def create_node(config: NodeConfig) -> 'BaseNode':
        """Create a node from configuration"""
        node_types = {
            'WorkNode': WorkNode,
            'RouterNode': RouterNode,
            'HTTPNode': HTTPNode
        }
        
        node_class = node_types.get(config.node_type)
        if not node_class:
            raise ValueError(f"Unknown node type: {config.node_type}")
        
        # Create node based on type
        if config.node_type == 'WorkNode':
            # Get work function from registry
            work_func = NodeRegistry.get_work_function(config.properties['work_type'])
            return node_class(config.node_id, work_func)
        
        elif config.node_type == 'RouterNode':
            # Convert serialized rules back to callable rules
            routing_rules = {
                NodeRegistry.get_routing_rule(rule_id): target
                for rule_id, target in config.properties['routing_rules'].items()
            }
            return node_class(config.node_id, routing_rules)
        
        elif config.node_type == 'HTTPNode':
            return node_class(config.node_id, config.properties['endpoint'])
        
        raise ValueError(f"Unable to create node of type: {config.node_type}")

class NodeRegistry:
    """Registry for work functions and routing rules"""
    _work_functions = {}
    _routing_rules = {}
    
    @classmethod
    def register_work_function(cls, name: str, func: callable):
        cls._work_functions[name] = func
    
    @classmethod
    def register_routing_rule(cls, name: str, rule: callable):
        cls._routing_rules[name] = rule
    
    @classmethod
    def get_work_function(cls, name: str) -> callable:
        return cls._work_functions.get(name)
    
    @classmethod
    def get_routing_rule(cls, name: str) -> callable:
        return cls._routing_rules.get(name)

# Example usage:
async def main():
    # Register work functions and routing rules
    async def example_work(data):
        await asyncio.sleep(1)
        return f"Processed: {data}"
    
    NodeRegistry.register_work_function("example_work", example_work)
    NodeRegistry.register_routing_rule("rule_1", lambda x: len(str(x)) > 10)
    
    # Create original network
    network = NodeNetwork()
    input_node = WorkNode("input", example_work)
    process_node = WorkNode("process", example_work)
    output_node = WorkNode("output", print)
    
    routing_rules = {
        lambda x: len(str(x)) > 10: "output",
        lambda x: True: "process"
    }
    router_node = RouterNode("router", routing_rules)
    
    network.add_node(input_node)
    network.add_node(process_node)
    network.add_node(output_node)
    network.add_node(router_node)
    
    network.connect_nodes("input", "router")
    network.connect_nodes("process", "output")
    
    # Save network configuration
    NodeSerializer.save_to_file(network, "network_config.json")
    
    # Load network configuration
    config = NodeSerializer.load_from_file("network_config.json")
    new_network = NodeFactory.create_network_from_config(config)
    
    # Start the new network
    await new_network.start_network()

if __name__ == "__main__":
    asyncio.run(main())