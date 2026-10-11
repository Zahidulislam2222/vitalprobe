import React from 'react'
import ReactDOM from 'react-dom/client'
import { MotionConfig } from 'motion/react'
import '@fontsource-variable/manrope'
import '@fontsource-variable/space-grotesk'
import 'lenis/dist/lenis.css'
import './styles.css'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MotionConfig reducedMotion="user"><App /></MotionConfig>
  </React.StrictMode>,
)
