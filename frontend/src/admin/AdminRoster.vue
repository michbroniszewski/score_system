<script setup lang="ts">
import { computed, reactive } from 'vue'
import { send } from '../api/client'
import type { RosterEntryOut, TeamOut } from '../api/types'
import { useApi } from '../api/useApi'
import LoadState from '../components/LoadState.vue'
import { useAction } from './useAction'

const props = defineProps<{ slug: string; teamId: string }>()
const teams = useApi<TeamOut[]>(() => `competitions/${props.slug}/teams`)
const roster = useApi<RosterEntryOut[]>(
  () => `competitions/${props.slug}/teams/${props.teamId}/roster`,
)
const team = computed(() => teams.data.value?.find((t) => t.id === props.teamId))

// Players of this competition who are in no roster now can join this one (a transfer).
const allEntries = useApi<RosterEntryOut[]>(() => `competitions/${props.slug}/roster`)
const freePlayers = computed(() => {
  const entries = allEntries.data.value ?? []
  const active = new Set(entries.filter((e) => !e.left_on).map((e) => e.player.id))
  const free = new Map(
    entries.filter((e) => !active.has(e.player.id)).map((e) => [e.player.id, e.player]),
  )
  return [...free.values()]
})

function reload() {
  roster.reload()
  allEntries.reload()
}

const form = reactive({
  playerId: '',
  firstName: '',
  lastName: '',
  number: '' as number | '',
  position: '',
  joinedOn: '',
})
const joining = useAction()
async function join() {
  const body = {
    ...(form.playerId
      ? { player_id: form.playerId }
      : { player: { first_name: form.firstName, last_name: form.lastName } }),
    number: form.number === '' ? null : form.number,
    position: form.position || null,
    joined_on: form.joinedOn || null,
  }
  const path = `competitions/${props.slug}/teams/${props.teamId}/roster`
  if (await joining.run(() => send('POST', path, body))) {
    Object.assign(form, {
      playerId: '',
      firstName: '',
      lastName: '',
      number: '',
      position: '',
      joinedOn: '',
    })
    reload()
  }
}

const leftOn = reactive<Record<string, string>>({})
const leaving = useAction()
async function leave(entryId: string) {
  const body = { left_on: leftOn[entryId] }
  if (await leaving.run(() => send('POST', `roster-entries/${entryId}/leave`, body))) reload()
}
</script>

<template>
  <LoadState
    :loading="roster.loading.value || teams.loading.value"
    :error="roster.error.value ?? teams.error.value"
  >
    <p class="meta">
      <RouterLink :to="{ name: 'admin-competition', params: { slug } }">
        ← Rozgrywki
      </RouterLink>
    </p>
    <h1>{{ team?.name }}: skład</h1>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Nr</th>
            <th class="left">
              Zawodnik
            </th>
            <th class="left">
              Pozycja
            </th>
            <th class="left">
              Od
            </th>
            <th class="left">
              Do
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="entry in roster.data.value"
            :key="entry.id"
          >
            <td>{{ entry.number ?? '' }}</td>
            <td class="left">
              {{ entry.player.first_name }} {{ entry.player.last_name }}
            </td>
            <td class="left">
              {{ entry.position ?? '' }}
            </td>
            <td class="left">
              {{ entry.joined_on ?? '' }}
            </td>
            <td class="left">
              <template v-if="entry.left_on">
                {{ entry.left_on }}
              </template>
              <form
                v-else
                class="inline"
                @submit.prevent="leave(entry.id)"
              >
                <input
                  v-model="leftOn[entry.id]"
                  type="date"
                  required
                  :aria-label="`Data odejścia: ${entry.player.last_name}`"
                >
                <button :disabled="leaving.busy.value">
                  Odchodzi
                </button>
              </form>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p
      v-if="leaving.error.value"
      class="error"
    >
      {{ leaving.error.value }}
    </p>

    <h2>Dodaj zawodnika</h2>
    <form
      class="form"
      @submit.prevent="join"
    >
      <label v-if="freePlayers.length">Zawodnik z tych rozgrywek
        <select v-model="form.playerId">
          <option value="">nowy zawodnik</option>
          <option
            v-for="player in freePlayers"
            :key="player.id"
            :value="player.id"
          >{{ player.first_name }} {{ player.last_name }}</option>
        </select>
      </label>
      <template v-if="!form.playerId">
        <label>Imię <input
          v-model="form.firstName"
          required
        ></label>
        <label>Nazwisko <input
          v-model="form.lastName"
          required
        ></label>
      </template>
      <label>Numer <input
        v-model.number="form.number"
        type="number"
        min="0"
        max="999"
      ></label>
      <label>Pozycja <input v-model="form.position"></label>
      <label>W składzie od <input
        v-model="form.joinedOn"
        type="date"
        :required="!!form.playerId"
      ></label>
      <button :disabled="joining.busy.value">
        Dodaj do składu
      </button>
      <p
        v-if="joining.error.value"
        class="error"
      >
        {{ joining.error.value }}
      </p>
    </form>
  </LoadState>
</template>
