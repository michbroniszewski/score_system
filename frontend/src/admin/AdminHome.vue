<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { send } from '../api/client'
import type { CompetitionOut } from '../api/types'
import { useApi } from '../api/useApi'
import LoadState from '../components/LoadState.vue'
import { useAction } from './useAction'

const router = useRouter()
const competitions = useApi<CompetitionOut[]>(() => 'competitions')
const presets = useApi<string[]>(() => 'presets')
const playoffs = useApi<string[]>(() => 'playoffs')
const form = reactive({
  name: '',
  slug: '',
  preset: 'volleyball',
  timezone: 'Europe/Warsaw',
  playoff: null as string | null,
})
const { busy, error, run } = useAction()

async function create() {
  const created = await run(() => send('POST', 'competitions', form))
  if (created) await router.push({ name: 'admin-competition', params: { slug: form.slug } })
}
</script>

<template>
  <h1>Panel administratora</h1>
  <p class="notice">
    Zmiany zapisują się w lokalnej bazie. Na stronę publiczną trafiają po
    <code>make export</code> i wypchnięciu <code>data/export/</code>.
  </p>
  <h2>Rozgrywki</h2>
  <LoadState
    :loading="competitions.loading.value"
    :error="competitions.error.value"
  >
    <ul class="cards">
      <li
        v-for="comp in competitions.data.value"
        :key="comp.slug"
      >
        <RouterLink :to="{ name: 'admin-competition', params: { slug: comp.slug } }">
          {{ comp.name }}
        </RouterLink>
      </li>
    </ul>
  </LoadState>
  <h2>Nowe rozgrywki</h2>
  <form
    class="form"
    @submit.prevent="create"
  >
    <label>Nazwa <input
      v-model="form.name"
      required
    ></label>
    <label>Identyfikator w adresie (małe litery, cyfry i myślniki)
      <input
        v-model="form.slug"
        required
        pattern="[a-z0-9]+(-[a-z0-9]+)*"
      >
    </label>
    <label>Dyscyplina
      <select v-model="form.preset">
        <option
          v-for="name in presets.data.value"
          :key="name"
        >{{ name }}</option>
      </select>
    </label>
    <label>Play-off (nie można go później zmienić)
      <select v-model="form.playoff">
        <option :value="null">bez play-off</option>
        <option
          v-for="name in playoffs.data.value"
          :key="name"
          :value="name"
        >{{ name }}</option>
      </select>
    </label>
    <label>Strefa czasowa <input
      v-model="form.timezone"
      required
    ></label>
    <button :disabled="busy">
      Utwórz
    </button>
    <p
      v-if="error"
      class="error"
    >
      {{ error }}
    </p>
  </form>
</template>
