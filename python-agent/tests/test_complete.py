#!/usr/bin/env python3
"""Test Telegram Bot ↔ Agent Handler connection"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

async def test_telegram_agent_bridge():
    """Test that Telegram bot properly bridges to Agent AI"""
    print("="*60)
    print("Testing Telegram ↔ Agent Bridge")
    print("="*60)
    
    from app.integrations.agent_handler import get_agent_handler, WorkflowState
    
    handler = get_agent_handler()
    
    # Test 1: Main menu workflow
    print("\n[Test 1] Main Menu Workflow")
    result = await handler.process_message(123, "Help")
    assert "text" in result
    assert "Main Menu" in result.get("text", "") or "Help" in result.get("text", "")
    print(f"✓ Help response received ({len(result['text'])} chars)")
    
    # Test 2: Project workflow
    print("\n[Test 2] Project Creation Workflow")
    result = await handler.process_message(123, "Create a new project")
    assert result.get("workflow_state") == WorkflowState.PROJECT_NAME.value
    print(f"✓ Project workflow started, state: {result.get('workflow_state')}")
    
    # Test 3: Continue project workflow
    result = await handler.process_message(123, "MyAwesomeProject")
    assert result.get("workflow_state") == WorkflowState.PROJECT_LANGUAGE.value
    print(f"✓ Project name captured, state: {result.get('workflow_state')}")
    
    # Clear context for next test
    handler.clear_context(123)
    
    # Test 4: Social workflow
    print("\n[Test 3] Social Media Workflow")
    result = await handler.process_message(123, "Post to social media")
    assert result.get("workflow_state") == WorkflowState.SOCIAL_PLATFORM.value
    print(f"✓ Social workflow started, state: {result.get('workflow_state')}")
    
    # Clear context
    handler.clear_context(123)
    
    # Test 5: Schedule workflow
    print("\n[Test 4] Schedule Workflow")
    result = await handler.process_message(123, "Schedule a task")
    assert result.get("workflow_state") == WorkflowState.SCHEDULE_TASK.value
    print(f"✓ Schedule workflow started, state: {result.get('workflow_state')}")
    
    # Clear context
    handler.clear_context(123)
    
    # Test 6: Restart workflow
    print("\n[Test 5] Restart Workflow")
    result = await handler.process_message(123, "Restart the agent")
    assert "restart" in result.get("text", "").lower() or "confirm" in result.get("text", "").lower()
    print(f"✓ Restart workflow initiated")
    
    # Clear context
    handler.clear_context(123)
    
    # Test 7: Shutdown workflow
    print("\n[Test 6] Shutdown Workflow")
    result = await handler.process_message(123, "Shutdown the agent")
    assert "shutdown" in result.get("text", "").lower() or "confirm" in result.get("text", "").lower()
    print(f"✓ Shutdown workflow initiated")
    
    # Clear context
    handler.clear_context(123)
    
    # Test 8: Natural language to AI
    print("\n[Test 7] Natural Language to AI")
    result = await handler.process_message(123, "Write a Python function to calculate fibonacci")
    assert "text" in result
    assert len(result["text"]) > 50  # AI should respond with actual content
    print(f"✓ AI responded to natural language ({len(result['text'])} chars)")
    
    # Test 9: Menu buttons
    print("\n[Test 8] Menu Button Responses")
    buttons_to_test = [
        ("🏗️ Project", "project"),
        ("📱 Social", "social"),
        ("📅 Schedule", "schedule"),
        ("❓ Help", "help"),
    ]
    
    for btn_text, expected in buttons_to_test:
        result = await handler.process_message(123, btn_text)
        text_lower = result.get("text", "").lower()
        assert expected in text_lower or result.get("workflow_state"), f"Button {btn_text} not working"
        print(f"✓ Button '{btn_text}' works")
        handler.clear_context(123)
    
    print("\n" + "="*60)
    print("All Telegram ↔ Agent Bridge Tests PASSED!")
    print("="*60)
    
    return True

async def test_skills_execution():
    """Test skill execution through agent"""
    print("\n" + "="*60)
    print("Testing Skills Execution")
    print("="*60)
    
    from app.skills.project_manager import ProjectManagerSkill
    from app.skills.social_poster import SocialPosterSkill
    from app.skills.system_controller import SystemControllerSkill
    
    # Test Project Manager
    print("\n[Test 9] Project Manager Skill")
    skill = ProjectManagerSkill()
    result = await skill.execute({
        "project_name": "test_bot_project",
        "language": "python",
        "framework": "fastapi",
        "goal": "A test API project"
    })
    assert result.success
    assert result.data
    assert "test_bot_project" in result.data.get("project_path", "")
    print(f"✓ Project created: {result.data.get('project_path')}")
    
    # Test Social Poster
    print("\n[Test 10] Social Poster Skill")
    social = SocialPosterSkill()
    result = await social.execute({
        "platform": "twitter",
        "content": "Testing the Ultimate Agent! #AI #Coding"
    })
    assert result.success
    assert result.data
    print(f"✓ Social post prepared for: {result.data.get('platform')}")
    
    # Test System Controller
    print("\n[Test 11] System Controller Skill")
    system = SystemControllerSkill()
    result = await system.execute({"action": "status"})
    assert result.success
    assert result.data and result.data.get("running") == True
    print(f"✓ System status retrieved")
    
    print("\n" + "="*60)
    print("All Skills Tests PASSED!")
    print("="*60)
    
    return True

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Ultimate Agent - Complete Integration Test")
    print("="*60)
    
    try:
        await test_telegram_agent_bridge()
        await test_skills_execution()
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("="*60)
        print("\nThe Ultimate Agent is fully connected:")
        print("✓ Telegram ↔ Agent AI Bridge Working")
        print("✓ 7-Button Menu Workflows Working")
        print("✓ Project Creation Working")
        print("✓ Social Media Workflow Working")
        print("✓ Task Scheduling Working")
        print("✓ System Control Working")
        print("✓ Skills System Working")
        print("\nRestart the agent to use the new features!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
