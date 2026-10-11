import { createContext, useContext, useEffect, useSyncExternalStore } from 'react'
import { useAnimationControls } from 'motion/react'
import { animation } from '../config'

export const MotionPaused = createContext(false)
function subscribePreference(onChange: () => void) {
  const preference = window.matchMedia(animation.reducedMotionQuery)
  preference.addEventListener('change', onChange)
  return () => preference.removeEventListener('change', onChange)
}
function readPreference() { return window.matchMedia(animation.reducedMotionQuery).matches }
export function useSystemReducedMotion() {
  return useSyncExternalStore(subscribePreference, readPreference, () => true)
}
export function useMotionPaused() {
  const preference = useSystemReducedMotion()
  const paused = useContext(MotionPaused)
  return Boolean(preference || paused)
}
export function useSettledMotion(reduce: boolean, entranceSeconds?: number) {
  const controls = useAnimationControls()
  useEffect(() => {
    if (reduce) {
      controls.stop()
      controls.set({ opacity: 1, y: 0 })
    } else if (entranceSeconds !== undefined) {
      void controls.start({ opacity: 1, y: 0, transition: { duration: entranceSeconds } })
    }
  }, [reduce, controls, entranceSeconds])
  return controls
}
