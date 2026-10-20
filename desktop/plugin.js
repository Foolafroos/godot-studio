/**
 * godot-studio — desktop half of the unified plugin package.
 *
 * Contributes: a statusbar chip (installed Godot version) and a "Godot builds"
 * pane (export presets + artifact state for a chosen project). Data comes from
 * this package's own backend (dashboard/plugin_api.py) via ctx.rest; the pane
 * degrades gracefully when the backend is off.
 *
 * Plain ESM, loaded uncompiled — UI is jsx() calls, not JSX syntax.
 */

import { cn, host, useQuery, Button, Input, EmptyState, Badge, Tip } from '@hermes/plugin-sdk'
import { useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'godot-studio'

let backend = null // set in register(); ctx.rest is plugin-scoped

function fmtSize(bytes) {
  if (!bytes) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  let v = bytes, i = 0
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i += 1 }
  return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`
}

function fmtTime(secs) {
  if (!secs) return ''
  const d = new Date(secs * 1000)
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function VersionChip() {
  const { data } = useQuery({
    queryKey: [ID, 'version'],
    queryFn: () => backend.rest('/version'),
    staleTime: 10 * 60 * 1000,
  })
  if (!data || !data.installed) return null
  const ver = String(data.version || '').split('\n')[0].replace(/^.*:?version:?\s*/i, '').trim()
  if (!ver) return null
  return jsx(Tip, {
    label: `Godot ${ver} — ${data.binary || ''}`,
    children: jsx('span', {
      className: cn(
        'inline-flex h-full items-center gap-1 px-1.5 text-[0.6875rem]',
        'text-(--ui-text-tertiary)'
      ),
      children: `godot ${ver}`
    })
  })
}

function BuildsPane() {
  const [project, setProject] = useState(() => {
    try { return ctxStorageGet('project') || '' } catch { return '' }
  })
  const [draft, setDraft] = useState(project)

  const { data, isFetching, refetch } = useQuery({
    queryKey: [ID, 'builds', project],
    queryFn: () => backend.rest(`/builds?project=${encodeURIComponent(project)}`),
    enabled: project.length > 0,
    staleTime: 15 * 1000,
  })

  const save = () => {
    const p = draft.trim()
    try { ctxStorageSet('project', p) } catch { /* storage unavailable */ }
    setProject(p)
    host.notify({ kind: 'info', message: `godot-studio: project set to ${p || '(cleared)'}` })
  }

  const builds = (data && data.builds) || []

  return jsxs('div', {
    className: 'flex h-full flex-col gap-2 p-3 text-sm',
    children: [
      jsxs('div', { className: 'flex items-center gap-2', children: [
        jsx(Input, {
          className: 'flex-1',
          placeholder: '/absolute/path/to/godot/project',
          value: draft,
          onChange: e => setDraft(e.target.value),
          onKeyDown: e => { if (e.key === 'Enter') save() }
        }),
        jsx(Button, { type: 'button', size: 'sm', onClick: save, children: 'Set' })
      ] }),
      jsxs('div', { className: 'flex items-center gap-2 text-(--ui-text-tertiary) text-xs', children: [
        jsx('span', { className: 'flex-1 truncate', children: project || 'no project configured' }),
        jsx(Button, {
          type: 'button', size: 'sm', variant: 'ghost',
          disabled: !project || isFetching,
          onClick: () => refetch(),
          children: isFetching ? 'refreshing…' : 'refresh'
        })
      ] }),
      !project
        ? jsx(EmptyState, { title: 'No project configured', description: 'Paste a Godot project path above. The pane lists its export presets and build artifacts.' })
        : builds.length === 0
          ? jsx(EmptyState, { title: 'No export presets', description: (data && data.error) || 'This project has no export_presets.cfg entries.' })
          : jsx('div', { className: 'flex flex-col gap-1 overflow-auto', children: builds.map(b =>
              jsxs('div', {
                className: cn(
                  'flex flex-col gap-0.5 rounded-md border border-(--ui-stroke-secondary) px-2 py-1.5',
                  !b.exists && 'opacity-60'
                ),
                children: [
                  jsxs('div', { className: 'flex items-center gap-2', children: [
                    jsx('span', { className: 'font-medium', children: b.preset }),
                    jsx(Badge, { children: b.exists ? fmtSize(b.size_bytes) : 'not built' })
                  ] }),
                  jsx('div', { className: 'truncate text-xs text-(--ui-text-quaternary)', children: b.artifact_path || b.export_path }),
                  b.exists ? jsx('div', { className: 'text-xs text-(--ui-text-quaternary)', children: fmtTime(b.modified) }) : null
                ]
              })
            ) })
    ]
  })
}

let ctxStorageRef = null
function ctxStorageGet(key) { return ctxStorageRef ? ctxStorageRef.get(key) : null }
function ctxStorageSet(key, value) { if (ctxStorageRef) ctxStorageRef.set(key, value) }

export default {
  id: ID,
  name: 'Godot Studio',
  defaultEnabled: false,
  register(ctx) {
    backend = ctx
    ctxStorageRef = ctx.storage

    ctx.register({
      id: 'chip',
      area: 'statusBar.right',
      order: 130,
      render: () => jsx(VersionChip, {})
    })

    ctx.register({
      id: 'builds-pane',
      area: 'panes',
      title: 'godot builds',
      data: { placement: 'right', width: '300px' },
      render: () => jsx(BuildsPane, {})
    })
  }
}
