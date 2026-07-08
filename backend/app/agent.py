import os
import json
import re
from typing import TypedDict, List, Dict, Any, Union
from datetime import datetime

# LangGraph and LangChain imports
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq

from .config import settings
from .tools import tools_list, log_interaction, edit_interaction, search_materials_and_samples, get_hcp_profile, generate_follow_up_tasks

# Define the state shape for LangGraph
class AgentState(TypedDict):
    messages: List[BaseMessage]
    form_data: Dict[str, Any]
    suggested_follow_ups: List[str]
    agent_response: str
    tool_called: str

# ----------------- Fallback Heuristics Parser (When Groq Key is Missing) -----------------
def run_heuristic_agent(user_message: str, current_form: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates LLM tool calling using pattern matching to ensure frontend functionality without Groq keys.
    """
    updated_form = dict(current_form)
    msg_lower = user_message.lower()
    bot_reply = ""
    tool_name = "None"

    # Tool 1: Log Interaction (ChatGPT style natural prompt)
    # Check if user is logging an interaction (e.g. met Dr. Smith, discussed X)
    if any(k in msg_lower for k in ["met ", "today ", "yesterday ", "log interaction", "discussed", "meeting with"]):
        tool_name = "log_interaction"
        # Extract HCP Name (looks for Dr. <Word> or Doctor <Word>)
        hcp_match = re.search(r'(dr\.\s+[a-zA-Z]+|dr\s+[a-zA-Z]+|doctor\s+[a-zA-Z]+)', user_message, re.IGNORECASE)
        if hcp_match:
            updated_form["hcp_name"] = hcp_match.group(1).title()
        else:
            updated_form["hcp_name"] = "Dr. Smith" # Default if not specified but logging

        # Extract Date
        if "today" in msg_lower:
            updated_form["date"] = datetime.now().strftime("%d-%m-%Y")
        elif "yesterday" in msg_lower:
            from datetime import timedelta
            updated_form["date"] = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")
        else:
            updated_form["date"] = datetime.now().strftime("%d-%m-%Y")

        # Set default time if empty
        if not updated_form.get("time"):
            updated_form["time"] = datetime.now().strftime("%H:%M")

        # Extract Sentiment
        if "positive" in msg_lower:
            updated_form["sentiment"] = "Positive"
        elif "negative" in msg_lower:
            updated_form["sentiment"] = "Negative"
        else:
            updated_form["sentiment"] = "Neutral"

        # Extract Interaction Type
        if "email" in msg_lower:
            updated_form["interaction_type"] = "Email"
        elif "call" in msg_lower:
            updated_form["interaction_type"] = "Call"
        else:
            updated_form["interaction_type"] = "Meeting"

        # Topics Discussed
        topic_match = re.search(r'discussed\s+(.*?)(\.|$|and sentiment|sentiment)', user_message, re.IGNORECASE)
        if topic_match:
            updated_form["topics_discussed"] = topic_match.group(1).strip().capitalize()
        else:
            updated_form["topics_discussed"] = "Discussed product efficacy and therapeutic benefits."

        # Add attendees
        hcp_name = updated_form["hcp_name"]
        updated_form["attendees"] = [hcp_name, "Rep (Me)"]

        # Materials / Brochures
        if "brochure" in msg_lower:
            updated_form["materials_shared"] = list(set(updated_form["materials_shared"] + ["CardioShield Brochure"]))
        if "pdf" in msg_lower or "clinical" in msg_lower:
            updated_form["materials_shared"] = list(set(updated_form["materials_shared"] + ["OncoBoost Phase III PDF"]))

        # Outcomes / Follow up actions
        updated_form["outcomes"] = "Shared marketing and clinical materials. Doctor was receptive."
        updated_form["follow_up_actions"] = "Follow up with additional study parameters and deliver sample kit."

        # Trigger AI follow-up recommendations
        updated_form["ai_suggested_follow_ups"] = ["Schedule follow-up meeting in 2 weeks"]
        if "oncoboost" in updated_form["topics_discussed"].lower() or "smith" in hcp_name.lower():
            updated_form["ai_suggested_follow_ups"].append("Send OncoBoost Phase III PDF")

        bot_reply = f"I've logged the interaction with {updated_form['hcp_name']} and automatically filled out the form fields. Please verify the details on the left."

    # Tool 2: Edit Interaction (e.g. name was actually Dr. John, sentiment negative)
    elif any(k in msg_lower for k in ["sorry", "correction", "change", "update", "edit", "was actually", "actually"]):
        tool_name = "edit_interaction"
        changes = []
        
        # Sentiment edits
        if "positive" in msg_lower:
            updated_form["sentiment"] = "Positive"
            changes.append("sentiment to Positive")
        elif "negative" in msg_lower:
            updated_form["sentiment"] = "Negative"
            changes.append("sentiment to Negative")
        elif "neutral" in msg_lower:
            updated_form["sentiment"] = "Neutral"
            changes.append("sentiment to Neutral")

        # Name edits (actually Dr. John)
        hcp_match = re.search(r'(dr\.\s+[a-zA-Z]+|dr\s+[a-zA-Z]+|doctor\s+[a-zA-Z]+)', user_message, re.IGNORECASE)
        if hcp_match:
            old_name = updated_form["hcp_name"]
            new_name = hcp_match.group(1).title()
            updated_form["hcp_name"] = new_name
            changes.append(f"HCP Name to {new_name}")
            # Update attendees if old name was there
            if old_name in updated_form["attendees"]:
                updated_form["attendees"] = [new_name if x == old_name else x for x in updated_form["attendees"]]
            else:
                updated_form["attendees"] = [new_name] + [a for a in updated_form["attendees"] if a != "Rep (Me)"] + ["Rep (Me)"]

        # Date edits
        date_match = re.search(r'(\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})', user_message)
        if date_match:
            updated_form["date"] = date_match.group(1)
            changes.append(f"date to {date_match.group(1)}")

        if changes:
            bot_reply = f"Updated: {', '.join(changes)}. Let me know if anything else needs correction."
        else:
            bot_reply = "I understand you want to modify something, but couldn't detect the fields. Try 'change sentiment to negative' or 'the name is actually Dr. John'."

    # Tool 3: Search Materials / Samples
    elif any(k in msg_lower for k in ["add ", "search ", "find ", "materials", "sample"]):
        tool_name = "search_materials_and_samples"
        if "oncoboost" in msg_lower:
            if "sample" in msg_lower:
                updated_form["samples_distributed"] = list(set(updated_form["samples_distributed"] + ["OncoBoost 10mg Starter Kit"]))
                bot_reply = "Added 'OncoBoost 10mg Starter Kit' to the samples distributed."
            else:
                updated_form["materials_shared"] = list(set(updated_form["materials_shared"] + ["OncoBoost Phase III PDF"]))
                bot_reply = "Added 'OncoBoost Phase III PDF' to the materials shared list."
        elif "cardio" in msg_lower:
            if "sample" in msg_lower:
                updated_form["samples_distributed"] = list(set(updated_form["samples_distributed"] + ["CardioShield 5mg Sample Pack"]))
                bot_reply = "Added 'CardioShield 5mg Sample Pack' to the samples distributed."
            else:
                updated_form["materials_shared"] = list(set(updated_form["materials_shared"] + ["CardioShield Brochure"]))
                bot_reply = "Added 'CardioShield Brochure' to the materials shared."
        else:
            bot_reply = "Searching... I found no matching materials. I can add standard materials like OncoBoost Phase III PDF or CardioShield Brochure if you request them."

    # Tool 4: Get HCP Profile
    elif any(k in msg_lower for k in ["profile", "history", "who is", "about dr"]):
        tool_name = "get_hcp_profile"
        hcp_match = re.search(r'(dr\.\s+[a-zA-Z]+|dr\s+[a-zA-Z]+|doctor\s+[a-zA-Z]+)', user_message, re.IGNORECASE)
        name = hcp_match.group(1).title() if hcp_match else "Dr. Sharma"
        
        if "sharma" in name.lower():
            bot_reply = f"HCP Profile for Dr. Sharma: Specialty is Immunology at University Research Hospital. History notes: 'Advisory board candidate. Extremely knowledgeable in immunotherapy pathways.'"
            updated_form["hcp_name"] = "Dr. Sharma"
            updated_form["attendees"] = ["Dr. Sharma", "Rep (Me)"]
        elif "smith" in name.lower():
            bot_reply = f"HCP Profile for Dr. Smith: Specialty is Oncology at City Cancer Center. History: 'Prefers clinical study data over slides.'"
            updated_form["hcp_name"] = "Dr. Smith"
            updated_form["attendees"] = ["Dr. Smith", "Rep (Me)"]
        else:
            bot_reply = f"HCP Profile for {name}: Not found in database. I can log an interaction with them as a new doctor."

    # Tool 5: Generate Follow-up Tasks
    elif any(k in msg_lower for k in ["suggest", "recommend", "follow-up", "next step", "tasks"]):
        tool_name = "generate_follow_up_tasks"
        updated_form["ai_suggested_follow_ups"] = [
            "Schedule follow-up meeting in 2 weeks",
            "Send OncoBoost Phase III PDF",
            "Add Dr. Sharma to advisory board invite list"
        ]
        bot_reply = "Generated 3 AI suggested follow-up tasks based on standard protocols. They are displayed at the bottom left."

    # General chat response
    else:
        bot_reply = "Hello! I am your HCP Interaction assistant. You can log an interaction by typing e.g., 'Met Dr. Smith today and discussed OncoBoost efficiency. Sentiment was positive.'"

    return {
        "form_data": updated_form,
        "reply": bot_reply,
        "tool_called": tool_name
    }

# ----------------- LangGraph Node Logic (When Groq Key Is Available) -----------------
def agent_node(state: AgentState):
    """
    Decides whether to execute a tool or send a response based on the conversation history.
    """
    messages = state["messages"]
    form_data = state["form_data"]

    # If GROQ_API_KEY is not defined, run the heuristic parser
    if not settings.GROQ_API_KEY or len(settings.GROQ_API_KEY.strip()) < 5:
        # Run fallback
        last_message = messages[-1].content
        result = run_heuristic_agent(last_message, form_data)
        
        # Append AI response to messages
        new_messages = list(messages) + [AIMessage(content=result["reply"])]
        
        return {
            "messages": new_messages,
            "form_data": result["form_data"],
            "suggested_follow_ups": result["form_data"].get("ai_suggested_follow_ups", []),
            "agent_response": result["reply"],
            "tool_called": result["tool_called"]
        }

    # If API key is available, initialize Groq Chat Model
    try:
        llm = ChatGroq(
            temperature=0.1,
            model_name="gemma2-9b-it",
            groq_api_key=settings.GROQ_API_KEY
        )
        
        # System instructions explaining the dual interface, the left form state, and the five tools
        system_prompt = f"""You are the AI Assistant for an AI-First CRM HCP Module, paired with a Sales Rep logging an interaction.
On the left side of the screen is an Interaction Form. Your job is to listen to the Sales Rep's input, answer questions, and USE your tools to control the left-side form.
DO NOT expect the user to fill the form. YOU control it.

The current state of the left form is:
{json.dumps(form_data, indent=2)}

You have access to 5 tools. Call them whenever appropriate:
1. `log_interaction`: Extracts fields from a natural description to fill out the form.
2. `edit_interaction`: Modifies a specific field when the user corrects a detail.
3. `search_materials_and_samples`: Adds materials (clinical PDFs, brochures) or samples (vial kits, starter packs) to the form.
4. `get_hcp_profile`: Looks up profile details of an HCP.
5. `generate_follow_up_tasks`: Suggests follow-up actions.

Instructions:
- If the user says: "Today I met with Dr. Smith and discussed product X efficiency. Sentiment was positive and I shared brochures", you MUST call `log_interaction` with arguments matching Dr. Smith, positive sentiment, date, topics, etc.
- If the user corrects a detail like: "Sorry, the name was actually Dr. John and sentiment negative", you MUST call `edit_interaction` to change those fields, leaving everything else the same.
- If the user wants to add/search brochures or samples, call `search_materials_and_samples`.
- If the user asks about the doctor's profile or preferences, call `get_hcp_profile`.
- If the user wants follow-up suggestions, call `generate_follow_up_tasks`.

If no tool is needed, respond politely to the user.
"""
        
        # Bind tools to ChatGroq
        llm_with_tools = llm.bind_tools(tools_list)
        
        # Prep messages
        formatted_messages = [SystemMessage(content=system_prompt)]
        # Filter and add conversation history (limit to last 10 messages for safety)
        for msg in messages[-10:]:
            formatted_messages.append(msg)
            
        response = llm_with_tools.invoke(formatted_messages)
        
        # Check if the LLM called a tool
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_call = response.tool_calls[0]
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            # Execute the correct tool locally
            tool_output = ""
            if tool_name == "log_interaction":
                tool_output = log_interaction.invoke(tool_args)
                extracted = json.loads(tool_output)
                # Merge into form data
                for k, v in extracted.items():
                    if v is not None:
                        form_data[k] = v
                # Generate default suggestions for follow-ups when logging
                form_data["ai_suggested_follow_ups"] = ["Schedule follow-up meeting in 2 weeks"]
                if "oncoboost" in str(extracted.get("topics_discussed", "")).lower():
                    form_data["ai_suggested_follow_ups"].append("Send OncoBoost Phase III PDF")
                reply_msg = f"I have processed your log. Extracted details for {form_data['hcp_name']} and populated the form on the left."
                
            elif tool_name == "edit_interaction":
                tool_output = edit_interaction.invoke(tool_args)
                edit_details = json.loads(tool_output)
                field = edit_details["field"]
                val = edit_details["value"]
                form_data[field] = val
                
                # If editing HCP name, update attendees too
                if field == "hcp_name":
                    form_data["attendees"] = [val, "Rep (Me)"]
                    
                reply_msg = f"Done. Updated the field '{field}' to '{val}'."
                
            elif tool_name == "search_materials_and_samples":
                tool_output = search_materials_and_samples.invoke(tool_args)
                res = json.loads(tool_output)
                cat = res["category"]
                matched_items = res["results"]
                
                if matched_items:
                    item_name = matched_items[0]["name"]
                    if cat == "material":
                        form_data["materials_shared"] = list(set(form_data.get("materials_shared", []) + [item_name]))
                        reply_msg = f"Added '{item_name}' to the materials shared list."
                    else:
                        form_data["samples_distributed"] = list(set(form_data.get("samples_distributed", []) + [item_name]))
                        reply_msg = f"Added '{item_name}' to the samples distributed."
                else:
                    reply_msg = f"Searched for '{res['query']}', but found no matching catalog item."
                    
            elif tool_name == "get_hcp_profile":
                tool_output = get_hcp_profile.invoke(tool_args)
                res = json.loads(tool_output)
                if res["found"]:
                    prof = res["profile"]
                    form_data["hcp_name"] = prof["name"]
                    form_data["attendees"] = [prof["name"], "Rep (Me)"]
                    reply_msg = f"Retrieved profile for {prof['name']} ({prof['specialty']}). Notes: {prof['history_notes']}"
                else:
                    reply_msg = res["message"]
                    
            elif tool_name == "generate_follow_up_tasks":
                tool_output = generate_follow_up_tasks.invoke(tool_args)
                res = json.loads(tool_output)
                sugs = res["suggestions"]
                form_data["ai_suggested_follow_ups"] = list(set(form_data.get("ai_suggested_follow_ups", []) + sugs))
                reply_msg = f"Suggested follow-up tasks generated: {', '.join(sugs)}"
                
            else:
                reply_msg = "Tool executed, but no handler defined for it."
                
            new_messages = list(messages) + [AIMessage(content=reply_msg)]
            return {
                "messages": new_messages,
                "form_data": form_data,
                "suggested_follow_ups": form_data.get("ai_suggested_follow_ups", []),
                "agent_response": reply_msg,
                "tool_called": tool_name
            }
        else:
            # Just plain AI chat response
            reply_msg = response.content
            new_messages = list(messages) + [AIMessage(content=reply_msg)]
            return {
                "messages": new_messages,
                "form_data": form_data,
                "suggested_follow_ups": form_data.get("ai_suggested_follow_ups", []),
                "agent_response": reply_msg,
                "tool_called": "None"
            }
            
    except Exception as e:
        print(f"Error executing ChatGroq: {e}. Falling back to heuristic mode.")
        # Fallback in case of API error or invalid token
        last_message = messages[-1].content
        result = run_heuristic_agent(last_message, form_data)
        
        # Append AI response to messages
        new_messages = list(messages) + [AIMessage(content=result["reply"])]
        
        return {
            "messages": new_messages,
            "form_data": result["form_data"],
            "suggested_follow_ups": result["form_data"].get("ai_suggested_follow_ups", []),
            "agent_response": result["reply"],
            "tool_called": result["tool_called"]
        }

# ----------------- LangGraph Graph Construction -----------------
def build_agent_graph():
    # Define a simple LangGraph Workflow
    workflow = StateGraph(AgentState)
    
    # Add our agent execution node
    workflow.add_node("agent", agent_node)
    
    # Set the entry point
    workflow.set_entry_point("agent")
    
    # We exit after the agent node since tool execution and state changes are handled in the node logic
    workflow.add_edge("agent", END)
    
    # Compile graph
    return workflow.compile()

# Compile the graph
graph_agent = build_agent_graph()

def run_chat_agent(message: str, current_form: Dict[str, Any], chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Helper function to run our LangGraph compiled graph.
    """
    # Build messages history list
    messages = []
    if chat_history:
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
                
    # Add new user message
    messages.append(HumanMessage(content=message))
    
    initial_state = {
        "messages": messages,
        "form_data": current_form,
        "suggested_follow_ups": current_form.get("ai_suggested_follow_ups", []),
        "agent_response": "",
        "tool_called": "None"
    }
    
    # Run the graph
    final_state = graph_agent.invoke(initial_state)
    
    return {
        "message": final_state["agent_response"],
        "form_data": final_state["form_data"],
        "suggested_follow_ups": final_state["suggested_follow_ups"],
        "tool_called": final_state["tool_called"]
    }
