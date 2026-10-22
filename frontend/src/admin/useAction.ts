import { ref } from 'vue'

// Runs a change (an API call) and keeps its error message for the form to show.
export function useAction() {
  const busy = ref(false)
  const error = ref<string | null>(null)

  async function run(action: () => Promise<unknown>): Promise<boolean> {
    busy.value = true
    error.value = null
    try {
      await action()
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      return false
    } finally {
      busy.value = false
    }
  }

  return { busy, error, run }
}
