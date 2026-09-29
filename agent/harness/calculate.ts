/**
 * Harness adapter — `calculate`, a side-effect-free arithmetic tool.
 *
 * `calculate` evaluates an infix arithmetic expression with a hand-written
 * recursive-descent parser over a fixed grammar. It performs no I/O, touches
 * no filesystem, network, shell, environment or clock, and never uses `eval`
 * or the `Function` constructor: the evaluator only sees digits, the five
 * arithmetic operators, parentheses, and whitespace, so no host capability is
 * reachable from the input.
 */
import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'a0-calculate'

export const inject = ['tools']

const SUPPORTED =
  'Supported input: a single arithmetic expression over decimal numbers (optionally in exponent form) '
  + 'using + - * / %, unary + -, parentheses, and whitespace. Anything else is rejected, as is division by zero.'

class ExpressionError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ExpressionError'
  }
}

function formatNumber(value: number): string {
  return Object.is(value, -0) ? '0' : String(value)
}

/** Recursive-descent evaluator that never invokes a host evaluator.
 * @param input - the raw expression text.
 * @returns the evaluated number.
 * @throws ExpressionError when the text is not a valid expression in the grammar.
 */
export function evaluateExpression(input: string): number {
  const text = input
  let index = 0

  const skipSpaces = (): void => {
    while (index < text.length && (text[index] === ' ' || text[index] === '\t' || text[index] === '\n' || text[index] === '\r')) index += 1
  }

  const peek = (): string | undefined => {
    skipSpaces()
    return index < text.length ? text[index] : undefined
  }

  /** One number literal: digits with an optional fraction and exponent. */
  const readNumber = (): number => {
    skipSpaces()
    const start = index
    while (index < text.length && text[index]! >= '0' && text[index]! <= '9') index += 1
    if (text[index] === '.') {
      index += 1
      while (index < text.length && text[index]! >= '0' && text[index]! <= '9') index += 1
    }
    if (index === start || text.slice(start, index) === '.') {
      throw new ExpressionError(`Expected a number at position ${start}`)
    }
    const digits = text[index] === 'e' || text[index] === 'E'
    if (digits) {
      const exponentStart = index
      index += 1
      if (text[index] === '+' || text[index] === '-') index += 1
      const exponentDigits = index
      while (index < text.length && text[index]! >= '0' && text[index]! <= '9') index += 1
      if (index === exponentDigits) index = exponentStart
    }
    const value = Number(text.slice(start, index))
    if (!Number.isFinite(value)) throw new ExpressionError(`"${text.slice(start, index)}" is not a finite number`)
    return value
  }

  /** A primary is a number or a parenthesized expression. */
  const readPrimary = (): number => {
    const next = peek()
    if (next === undefined) throw new ExpressionError('Unexpected end of expression')
    if (next === '(') {
      index += 1
      const value = readAdditive()
      if (peek() !== ')') throw new ExpressionError('Unbalanced parentheses: missing ")"')
      index += 1
      return value
    }
    if (next === ')') throw new ExpressionError('Unexpected ")"')
    return readNumber()
  }

  /** Unary plus/minus, and the only two characters that could ever look like a comment. */
  const readUnary = (): number => {
    const next = peek()
    if (next === '-') {
      index += 1
      return -readUnary()
    }
    if (next === '+') {
      index += 1
      return readUnary()
    }
    return readPrimary()
  }

  /** Multiplication, division, and remainder bind tighter than addition. */
  const readMultiplicative = (): number => {
    let value = readUnary()
    for (;;) {
      const next = peek()
      if (next !== '*' && next !== '/' && next !== '%') return value
      index += 1
      const right = readUnary()
      if ((next === '/' || next === '%') && right === 0) throw new ExpressionError(`Division by zero in "${input.trim()}"`)
      if (next === '*') value *= right
      else if (next === '/') value /= right
      else value %= right
    }
  }

  const readAdditive = (): number => {
    let value = readMultiplicative()
    for (;;) {
      const next = peek()
      if (next !== '+' && next !== '-') return value
      index += 1
      const right = readMultiplicative()
      value = next === '+' ? value + right : value - right
    }
  }

  if (text.trim() === '') throw new ExpressionError('The expression is empty')
  const result = readAdditive()
  skipSpaces()
  if (index !== text.length) throw new ExpressionError(`Unexpected "${text.slice(index)}" at position ${index}`)
  if (!Number.isFinite(result)) throw new ExpressionError('The result is not a finite number')
  return result
}

export function apply(ctx: Context): void {
  ctx.tools.register(defineTool({
    name: 'calculate',
    description:
      'Evaluate one arithmetic expression and return its exact numeric result. Use this for arithmetic instead of '
      + 'computing in your head: the result comes from a deterministic parser, not from the model. The tool is pure — '
      + 'it reads and writes nothing. ' + SUPPORTED,
    parameters: {
      expression: {
        type: 'string',
        required: true,
        description: 'Arithmetic expression to evaluate, e.g. "12 + 29" or "(3 * (4 + 5)) / 2".',
      },
    },
    output: {
      schema: {
        type: 'object',
        properties: {
          expression: { type: 'string' },
          value: { type: 'number' },
          result: { type: 'string' },
        },
        additionalProperties: false,
      },
      render: (_args, value) => [{ type: 'text', text: `${value.expression} = ${value.result}` }],
    },
    execute(args) {
      const value = evaluateExpression(args.expression)
      return Promise.resolve({
        expression: args.expression.trim(),
        value,
        result: formatNumber(value),
      })
    },
  }))

}
