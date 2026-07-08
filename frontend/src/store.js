import { configureStore, createSlice } from '@reduxjs/toolkit'

const initialFormState = {
  hcp_name: '',
  interaction_type: 'Meeting',
  date: '',
  time: '',
  attendees: [],
  topics_discussed: '',
  materials_shared: [],
  samples_distributed: [],
  sentiment: 'Neutral',
  outcomes: '',
  follow_up_actions: '',
  ai_suggested_follow_ups: []
}

const formSlice = createSlice({
  name: 'form',
  initialState: initialFormState,
  reducers: {
    updateForm: (state, action) => {
      return { ...state, ...action.payload }
    },
    resetForm: () => initialFormState,
    addMaterial: (state, action) => {
      if (!state.materials_shared.includes(action.payload)) {
        state.materials_shared.push(action.payload)
      }
    },
    removeMaterial: (state, action) => {
      state.materials_shared = state.materials_shared.filter(item => item !== action.payload)
    },
    addSample: (state, action) => {
      if (!state.samples_distributed.includes(action.payload)) {
        state.samples_distributed.push(action.payload)
      }
    },
    removeSample: (state, action) => {
      state.samples_distributed = state.samples_distributed.filter(item => item !== action.payload)
    },
    addAttendee: (state, action) => {
      if (!state.attendees.includes(action.payload)) {
        state.attendees.push(action.payload)
      }
    },
    removeAttendee: (state, action) => {
      state.attendees = state.attendees.filter(item => item !== action.payload)
    }
  }
})

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    messages: [
      {
        id: 'welcome',
        role: 'assistant',
        content: 'Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure") or ask for help.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ],
    isTyping: false
  },
  reducers: {
    addMessage: (state, action) => {
      state.messages.push({
        id: Math.random().toString(36).substring(2, 9),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        ...action.payload
      })
    },
    setTyping: (state, action) => {
      state.isTyping = action.payload
    },
    clearChat: (state) => {
      state.messages = [
        {
          id: 'welcome',
          role: 'assistant',
          content: 'Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure") or ask for help.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]
    }
  }
})

const catalogSlice = createSlice({
  name: 'catalog',
  initialState: {
    hcps: [],
    materials: [],
    samples: [],
    loading: false,
    error: null
  },
  reducers: {
    fetchStart: (state) => {
      state.loading = true
      state.error = null
    },
    fetchSuccess: (state, action) => {
      state.loading = false
      state.hcps = action.payload.hcps
      state.materials = action.payload.materials
      state.samples = action.payload.samples
    },
    fetchFailure: (state, action) => {
      state.loading = false
      state.error = action.payload
    }
  }
})

export const { updateForm, resetForm, addMaterial, removeMaterial, addSample, removeSample, addAttendee, removeAttendee } = formSlice.actions
export const { addMessage, setTyping, clearChat } = chatSlice.actions
export const { fetchStart, fetchSuccess, fetchFailure } = catalogSlice.actions

export const store = configureStore({
  reducer: {
    form: formSlice.reducer,
    chat: chatSlice.reducer,
    catalog: catalogSlice.reducer
  }
})
