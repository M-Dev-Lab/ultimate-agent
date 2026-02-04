#!/usr/bin/env python3
"""Test Ollama connection and agent functionality"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

async def test_ollama():
    """Test Ollama connection"""
    print("Testing Ollama connection...")
    
    from app.integrations.ollama import get_ollama_client
    
    ollama = get_ollama_client()
    
    print(f"Cloud mode: {ollama.is_cloud}")
    print(f"Local host: {ollama.local_host}")
    print(f"Local model: {ollama.local_model}")
    
    print("\nRunning health check...")
    health = await ollama.health_check()
    print(f"Health: {health}")
    
    if health.get("local"):
        print("\n✓ Ollama local is available")
        print(f"  Models: {health.get('models', [])}")
    else:
        print("\n✗ Ollama local not available")
    
    if health.get("cloud"):
        print("\n✓ Ollama cloud is available")
    else:
        print("\n✗ Ollama cloud not configured or unavailable")
    
    return health

async def test_agent_handler():
    """Test agent handler"""
    print("\n" + "="*50)
    print("Testing Agent Handler...")
    
    from app.integrations.agent_handler import get_agent_handler
    
    handler = get_agent_handler()
    
    result = await handler.process_message(
        user_id=12345,
        message="Create a Python FastAPI project"
    )
    
    print(f"Response: {result.get('text', 'No text')[:200]}...")
    
    return result

async def test_skills():
    """Test skills"""
    print("\n" + "="*50)
    print("Testing Skills...")
    
    from app.skills.project_manager import ProjectManagerSkill
    from app.skills.social_poster import SocialPosterSkill
    from app.skills.system_controller import SystemControllerSkill
    
    project_skill = ProjectManagerSkill()
    social_skill = SocialPosterSkill()
    system_skill = SystemControllerSkill()
    
    print(f"✓ Project Manager Skill: {project_skill.name}")
    print(f"✓ Social Poster Skill: {social_skill.name}")
    print(f"✓ System Controller Skill: {system_skill.name}")
    
    result = await project_skill.execute({
        "project_name": "test_project",
        "language": "python",
        "framework": "fastapi",
        "goal": "A test FastAPI project"
    })
    
    print(f"Project creation result: {result.success}")
    if result.data:
        print(f"  Project path: {result.data.get('project_path', 'N/A')}")
    
    return True

async def main():
    """Run all tests"""
    print("="*50)
    print("Ultimate Agent - Integration Tests")
    print("="*50)
    
    try:
        health = await test_ollama()
        await test_agent_handler()
        await test_skills()
        
        print("\n" + "="*50)
        print("All tests completed!")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
