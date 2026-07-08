import React, { useState, useEffect, useRef } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import {
  updateForm,
  resetForm,
  addMaterial,
  removeMaterial,
  addSample,
  removeSample,
  addAttendee,
  removeAttendee,
  addMessage,
  setTyping,
  clearChat,
  fetchStart,
  fetchSuccess,
  fetchFailure
} from './store'
import axios from 'axios'
import { 
  User, 
  Calendar, 
  Clock, 
  MessageSquare, 
  Plus, 
  Minus, 
  Mic, 
  Send, 
  CheckCircle2, 
  FileText, 
  Package, 
  ArrowRight,
  RefreshCw,
  Search,
  Sparkles,
  UserCheck,
  AlertTriangle,
  X
} from 'lucide-react'

// Set base URL for API requests (Vite proxy will handle this)
axios.defaults.baseURL = 'http://localhost:8000'

export default function App() {
  const dispatch = useDispatch()
  const form = useSelector((state) => state.form)
  const { messages, isTyping } = useSelector((state) => state.chat)
  const catalog = useSelector((state) => state.catalog)

  // Local state UI variables
  const [chatInput, setChatInput] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  
  // Modals state
  const [activeModal, setActiveModal] = useState(null) // 'material', 'sample', 'hcp', 'success'
  const [searchQuery, setSearchQuery] = useState('')
  const [interactionId, setInteractionId] = useState(null)
  const [errorMessage, setErrorMessage] = useState(null)

  const chatEndRef = useRef(null)

  // Fetch catalog data on load
  useEffect(() => {
    const fetchCatalog = async () => {
      dispatch(fetchStart())
      try {
        const [hcpsRes, matRes, sampRes] = await Promise.all([
          axios.get('/api/hcps'),
          axios.get('/api/materials'),
          axios.get('/api/samples')
        ])
        dispatch(fetchSuccess({
          hcps: hcpsRes.data,
          materials: matRes.data,
          samples: sampRes.data
        }))
      } catch (err) {
        console.error("Error loading catalog data:", err)
        dispatch(fetchFailure(err.message || 'Failed to load catalog data'))
      }
    }
    fetchCatalog()
    
    // Set current date/time on load if not set
    const today = new Date()
    const dd = String(today.getDate()).padStart(2, '0')
    const mm = String(today.getMonth() + 1).padStart(2, '0')
    const yyyy = today.getFullYear()
    const formattedDate = `${dd}-${mm}-${yyyy}`
    const formattedTime = today.toTimeString().split(' ')[0].substring(0, 5)
    
    dispatch(updateForm({
      date: formattedDate,
      time: formattedTime
    }))
  }, [dispatch])

  // Auto-scroll chat window
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Voice recording simulation timer
  useEffect(() => {
    let interval
    if (isRecording) {
      interval = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1)
      }, 1000)
    } else {
      setRecordingSeconds(0)
    }
    return () => clearInterval(interval)
  }, [isRecording])

  // Submit chat message to the agent
  const handleSendMessage = async (textToSend) => {
    const messageText = textToSend || chatInput
    if (!messageText.trim()) return

    // Add user message in chat
    dispatch(addMessage({ role: 'user', content: messageText }))
    if (!textToSend) setChatInput('')
    dispatch(setTyping(true))
    setErrorMessage(null)

    try {
      // Post message and current form state to backend LangGraph agent
      const response = await axios.post('/api/chat', {
        message: messageText,
        current_form: form
      })

      const { message, form_data } = response.data

      // Add assistant response in chat
      dispatch(addMessage({ role: 'assistant', content: message }))
      // Update form state with new fields
      dispatch(updateForm(form_data))
    } catch (err) {
      console.error("Error communicating with AI agent:", err)
      const errorMsg = err.response?.data?.detail || "Could not connect to the AI Assistant. Please check if the FastAPI server is running."
      setErrorMessage(errorMsg)
      dispatch(addMessage({
        role: 'assistant',
        content: "Sorry, I ran into an error trying to process your command. Let's make sure the backend is active."
      }))
    } finally {
      dispatch(setTyping(false))
    }
  }

  // Trigger Simulated Voice Note
  const handleVoiceNoteToggle = () => {
    if (isRecording) {
      setIsRecording(false)
      // Send a rich clinical transcript to the agent representing the voice note
      const transcript = "Today I met Dr. Smith at City Cancer Center to discuss OncoBoost efficacy and patient safety. He had a positive sentiment and wanted to check the clinical trials. I shared the OncoBoost Phase III PDF and provided him with two OncoBoost 10mg Starter Kits."
      handleSendMessage(transcript)
    } else {
      setIsRecording(true)
      // Simulate listening for 3 seconds then stop automatically
      setTimeout(() => {
        setIsRecording(false)
        const transcript = "Today I met Dr. Smith at City Cancer Center to discuss OncoBoost efficacy and patient safety. He had a positive sentiment and wanted to check the clinical trials. I shared the OncoBoost Phase III PDF and provided him with two OncoBoost 10mg Starter Kits."
        handleSendMessage(transcript)
      }, 3500)
    }
  }

  // Handle suggested follow-up clicks
  const handleSuggestionClick = (suggestionText) => {
    // If they click on it, we will feed the action back to the agent so that it performs the change
    handleSendMessage(`Add the suggestion: "${suggestionText}"`)
  }

  // Final submit to save interaction to database
  const handleSubmitForm = async (e) => {
    e.preventDefault()
    if (!form.hcp_name) {
      setErrorMessage("An HCP Name is required to log the interaction. Please chat with the AI (e.g. 'Met Dr. Smith') to set it.")
      return
    }

    try {
      const response = await axios.post('/api/interactions', form)
      setInteractionId(response.data.interaction_id)
      setActiveModal('success')
    } catch (err) {
      console.error("Error saving interaction:", err)
      setErrorMessage(err.response?.data?.detail || "Failed to log interaction to CRM database.")
    }
  }

  // Reset screen
  const handleReset = () => {
    dispatch(resetForm())
    dispatch(clearChat())
    setErrorMessage(null)
    const today = new Date()
    const dd = String(today.getDate()).padStart(2, '0')
    const mm = String(today.getMonth() + 1).padStart(2, '0')
    const yyyy = today.getFullYear()
    dispatch(updateForm({
      date: `${dd}-${mm}-${yyyy}`,
      time: today.toTimeString().split(' ')[0].substring(0, 5)
    }))
  }

  // Handle Manual attendee addition (as fallback helper)
  const handleAddAttendeeInput = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      const val = e.target.value.trim()
      if (val) {
        dispatch(addAttendee(val))
        e.target.value = ''
      }
    }
  }

  // Modal Item Selections
  const handleSelectCatalogItem = (item) => {
    if (activeModal === 'material') {
      dispatch(addMaterial(item.name))
      // Inform the agent so it knows
      dispatch(addMessage({
        role: 'assistant',
        content: `I've added the material '${item.name}' to the list.`
      }))
    } else if (activeModal === 'sample') {
      dispatch(addSample(item.name))
      dispatch(addMessage({
        role: 'assistant',
        content: `I've added the sample kit '${item.name}' to the list.`
      }))
    } else if (activeModal === 'hcp') {
      dispatch(updateForm({ 
        hcp_name: item.name,
        attendees: [item.name, "Rep (Me)"]
      }))
      dispatch(addMessage({
        role: 'assistant',
        content: `Selected profile for ${item.name}. Pre-populated attendees list.`
      }))
    }
    setActiveModal(null)
    setSearchQuery('')
  }

  // Filter Catalog lists based on Search Query
  const filteredCatalogItems = () => {
    const q = searchQuery.toLowerCase()
    if (activeModal === 'material') {
      return catalog.materials.filter(m => m.name.toLowerCase().includes(q) || m.product.toLowerCase().includes(q))
    } else if (activeModal === 'sample') {
      return catalog.samples.filter(s => s.name.toLowerCase().includes(q) || s.product.toLowerCase().includes(q))
    } else if (activeModal === 'hcp') {
      return catalog.hcps.filter(h => h.name.toLowerCase().includes(q) || h.specialty.toLowerCase().includes(q))
    }
    return []
  }

  return (
    <>
      <header className="app-header">
        <h1>CRM Log HCP Interaction</h1>
        <div className="status-badge">
          <div className="status-dot"></div>
          <span>AI-Powered Mode Active</span>
        </div>
      </header>

      <main className="app-container">
        {/* Left Side: Interaction Details Panel */}
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Interaction Details</h2>
              <span className="panel-subtitle">Review the AI populated fields</span>
            </div>
            <button className="sub-panel-btn" onClick={handleReset}>
              <RefreshCw size={14} /> Clear Form
            </button>
          </div>

          <form onSubmit={handleSubmitForm} className="form-scroll-container">
            {errorMessage && (
              <div style={{
                backgroundColor: 'var(--danger-light)',
                border: '1px solid var(--danger)',
                color: 'var(--danger)',
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-md)',
                marginBottom: '1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: '0.85rem'
              }}>
                <AlertTriangle size={16} />
                <span>{errorMessage}</span>
              </div>
            )}

            <div className="form-grid">
              {/* HCP Name */}
              <div className="form-group">
                <label className="form-label">HCP Name</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="text"
                    value={form.hcp_name}
                    placeholder="Search or select HCP..."
                    className="form-input ai-controlled"
                    readOnly
                  />
                  <button 
                    type="button" 
                    onClick={() => setActiveModal('hcp')}
                    style={{
                      position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
                      background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer'
                    }}
                  >
                    <Search size={16} />
                  </button>
                </div>
              </div>

              {/* Interaction Type */}
              <div className="form-group">
                <label className="form-label">Interaction Type</label>
                <select
                  value={form.interaction_type}
                  className="form-input ai-controlled"
                  disabled
                >
                  <option value="Meeting">Meeting</option>
                  <option value="Call">Call</option>
                  <option value="Email">Email</option>
                  <option value="Event">Event</option>
                </select>
              </div>

              {/* Date */}
              <div className="form-group">
                <label className="form-label">Date</label>
                <input
                  type="text"
                  value={form.date}
                  placeholder="DD-MM-YYYY"
                  className="form-input ai-controlled"
                  readOnly
                />
              </div>

              {/* Time */}
              <div className="form-group">
                <label className="form-label">Time</label>
                <input
                  type="text"
                  value={form.time}
                  placeholder="HH:MM"
                  className="form-input ai-controlled"
                  readOnly
                />
              </div>

              {/* Attendees */}
              <div className="form-group form-group-full">
                <label className="form-label">Attendees</label>
                <div className="attendees-container">
                  {form.attendees.map(name => (
                    <span key={name} className="attendee-tag">
                      <User size={12} style={{ color: 'var(--text-muted)' }} />
                      {name}
                      <button 
                        type="button" 
                        className="attendee-remove" 
                        onClick={() => dispatch(removeAttendee(name))}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  <input
                    type="text"
                    placeholder="Enter names or search..."
                    className="form-input"
                    style={{ border: 'none', background: 'none', width: 'auto', flex: 1, minWidth: '150px', padding: 0 }}
                    onKeyDown={handleAddAttendeeInput}
                  />
                </div>
              </div>

              {/* Topics Discussed */}
              <div className="form-group form-group-full">
                <label className="form-label">Topics Discussed</label>
                <textarea
                  value={form.topics_discussed}
                  placeholder="Enter key discussion points..."
                  className="form-input form-textarea ai-controlled"
                  readOnly
                />
              </div>

              {/* Voice Note Simulation */}
              <div className="voice-note-section">
                <button
                  type="button"
                  onClick={handleVoiceNoteToggle}
                  className={`voice-btn ${isRecording ? 'recording' : ''}`}
                >
                  <Mic size={14} />
                  <span>
                    {isRecording 
                      ? `Listening... (${recordingSeconds}s) click to stop` 
                      : 'Summarize from Voice Note (Requires Consent)'}
                  </span>
                </button>
              </div>

              {/* Materials Shared Sub-panel */}
              <div className="sub-panel-card">
                <div className="sub-panel-header">
                  <span className="sub-panel-title">Materials Shared</span>
                  <button type="button" className="sub-panel-btn" onClick={() => setActiveModal('material')}>
                    <Search size={12} /> Search/Add
                  </button>
                </div>
                <div className="items-list">
                  {form.materials_shared.length === 0 ? (
                    <div className="empty-placeholder">No materials added.</div>
                  ) : (
                    form.materials_shared.map(item => (
                      <div key={item} className="item-tag">
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <FileText size={12} /> {item}
                        </span>
                        <button type="button" onClick={() => dispatch(removeMaterial(item))}>
                          <Minus size={12} />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Samples Distributed Sub-panel */}
              <div className="sub-panel-card">
                <div className="sub-panel-header">
                  <span className="sub-panel-title">Samples Distributed</span>
                  <button type="button" className="sub-panel-btn" onClick={() => setActiveModal('sample')}>
                    <Plus size={12} /> Add Sample
                  </button>
                </div>
                <div className="items-list">
                  {form.samples_distributed.length === 0 ? (
                    <div className="empty-placeholder">No samples added.</div>
                  ) : (
                    form.samples_distributed.map(item => (
                      <div key={item} className="item-tag">
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <Package size={12} /> {item}
                        </span>
                        <button type="button" onClick={() => dispatch(removeSample(item))}>
                          <Minus size={12} />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Sentiment Options */}
              <div className="sentiment-container">
                <label className="form-label">Observed/Inferred HCP Sentiment</label>
                <div className="sentiment-options">
                  {['Positive', 'Neutral', 'Negative'].map(mode => {
                    const emojis = { Positive: '😊', Neutral: '😐', Negative: '😞' }
                    return (
                      <label key={mode} className="sentiment-label">
                        <input
                          type="radio"
                          name="sentiment"
                          value={mode}
                          checked={form.sentiment === mode}
                          className="sentiment-radio"
                          disabled
                        />
                        <span className="sentiment-emoji">{emojis[mode]}</span>
                        <span>{mode}</span>
                      </label>
                    )
                  })}
                </div>
              </div>

              {/* Outcomes */}
              <div className="form-group form-group-full">
                <label className="form-label">Outcomes</label>
                <textarea
                  value={form.outcomes}
                  placeholder="Key outcomes or agreements..."
                  className="form-input form-textarea ai-controlled"
                  readOnly
                />
              </div>

              {/* Follow-up Actions */}
              <div className="form-group form-group-full">
                <label className="form-label">Follow-up Actions</label>
                <textarea
                  value={form.follow_up_actions}
                  placeholder="Enter next steps or tasks..."
                  className="form-input form-textarea ai-controlled"
                  readOnly
                />
              </div>

              {/* AI Suggested Follow-ups */}
              <div className="suggestions-box">
                <h3 className="suggestions-title">
                  <Sparkles size={14} /> AI Suggested Follow-ups:
                </h3>
                <div className="suggestions-list">
                  {form.ai_suggested_follow_ups.length === 0 ? (
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      No follow-ups suggested yet. Log an interaction or topics first.
                    </div>
                  ) : (
                    form.ai_suggested_follow_ups.map((sug, i) => (
                      <button
                        type="button"
                        key={i}
                        className="suggestion-item"
                        onClick={() => handleSuggestionClick(sug)}
                      >
                        + {sug}
                      </button>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="form-footer-actions">
              <button type="button" className="btn-cancel" onClick={handleReset}>Reset</button>
              <button type="submit" className="btn-submit">Submit Interaction</button>
            </div>
          </form>
        </section>

        {/* Right Side: AI Assistant Chat Panel */}
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">
                <Sparkles size={16} style={{ color: 'var(--primary)' }} /> AI Assistant
              </h2>
              <span className="panel-subtitle">Log interaction via chat</span>
            </div>
          </div>

          <div className="chat-container">
            <div className="chat-history">
              {messages.map((msg) => (
                <div key={msg.id} className={`message-bubble ${msg.role}`}>
                  <p>{msg.content}</p>
                  <div className="message-time">{msg.timestamp}</div>
                </div>
              ))}

              {isTyping && (
                <div className="typing-indicator">
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input message bar */}
            <div className="chat-input-bar">
              <input
                type="text"
                placeholder="Describe interaction..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                className="chat-input"
                disabled={isTyping}
              />
              <button
                type="button"
                onClick={() => handleSendMessage()}
                className="btn-icon"
                disabled={isTyping || !chatInput.trim()}
              >
                <Send size={14} /> Log
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* Catalog Search / Add Modals */}
      {['material', 'sample', 'hcp'].includes(activeModal) && (
        <div className="modal-overlay" onClick={() => setActiveModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="panel-header">
              <h3 className="panel-title">
                {activeModal === 'material' && "Search & Add Materials Shared"}
                {activeModal === 'sample' && "Search & Add Samples Distributed"}
                {activeModal === 'hcp' && "Select Healthcare Professional"}
              </h3>
              <button 
                type="button" 
                onClick={() => setActiveModal(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <input
                type="text"
                className="modal-search-input"
                placeholder="Type query to search catalog..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoFocus
              />
              <div className="modal-list">
                {filteredCatalogItems().length === 0 ? (
                  <div className="empty-placeholder">No matching catalog items found.</div>
                ) : (
                  filteredCatalogItems().map((item, index) => (
                    <div 
                      key={index} 
                      className="modal-list-item"
                      onClick={() => handleSelectCatalogItem(item)}
                    >
                      <div>
                        <div className="modal-list-item-title">{item.name}</div>
                        <div className="modal-list-item-sub">
                          {activeModal === 'material' && `${item.type} • Product: ${item.product}`}
                          {activeModal === 'sample' && `Dosage: ${item.dosage || 'Standard'} • Product: ${item.product}`}
                          {activeModal === 'hcp' && `${item.specialty} • ${item.organization}`}
                        </div>
                      </div>
                      <Plus size={14} style={{ color: 'var(--primary)' }} />
                    </div>
                  ))
                )}
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => setActiveModal(null)}>Cancel</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Success Modal */}
      {activeModal === 'success' && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ textAlign: 'center', padding: '2rem 1.5rem', maxWidth: '400px' }}>
            <div style={{ color: 'var(--success)', display: 'grid', placeItems: 'center', marginBottom: '1rem' }}>
              <CheckCircle2 size={48} />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>Logged Successfully</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
              The interaction has been synchronized with the main CRM database. Interaction Record ID: <strong>{interactionId}</strong>
            </p>
            <button 
              type="button" 
              className="btn-submit" 
              onClick={() => {
                setActiveModal(null)
                handleReset()
              }}
              style={{ width: '100%' }}
            >
              Done
            </button>
          </div>
        </div>
      )}
    </>
  )
}
