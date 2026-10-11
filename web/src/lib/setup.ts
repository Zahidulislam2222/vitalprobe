import { content } from './content'

// POSIX shell quoting prevents a configured URL from becoming a shell expression.
export function quoteShell(value: string) {
  return `'${value.replaceAll("'", "'\"'\"'")}'`
}
export function setupCommands(methodId: string, repositoryUrl: string) {
  const method = content.quickstart.methods.find((item) => item.id === methodId)
  if (!method) throw new Error('Unknown setup method')
  return [...content.quickstart.bootstrap, ...method.commands].map((command) =>
    command.replaceAll('{{repository}}', quoteShell(repositoryUrl)))
}
