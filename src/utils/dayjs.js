import dayjs from 'dayjs'
import customParseFormat from 'dayjs/plugin/customParseFormat'
import localizedFormat from 'dayjs/plugin/localizedFormat'
import relativeTime from 'dayjs/plugin/relativeTime'
import utc from 'dayjs/plugin/utc'

import 'dayjs/locale/en'
import 'dayjs/locale/es'
import 'dayjs/locale/ja'
import 'dayjs/locale/ko'
import 'dayjs/locale/pt-br'
import 'dayjs/locale/ru'
import 'dayjs/locale/vi'
import 'dayjs/locale/zh-cn'
import 'dayjs/locale/zh-tw'

dayjs.extend(utc)
dayjs.extend(relativeTime)
dayjs.extend(customParseFormat)
dayjs.extend(localizedFormat)

const localeAliases = {
  zh: 'zh-cn',
  'zh-cn': 'zh-cn',
  'zh-hans': 'zh-cn',
  zh_hant: 'zh-tw',
  'zh-hant': 'zh-tw',
  'zh-tw': 'zh-tw',
  en: 'en',
  ja: 'ja',
  pt_br: 'pt-br',
  'pt-br': 'pt-br',
  es: 'es',
  ru: 'ru',
  ko: 'ko',
  vi: 'vi'
}

export function setDayjsLocale(locale) {
  const normalizedLocale = (locale || 'en').toLowerCase()
  const dayjsLocale =
    localeAliases[normalizedLocale] || localeAliases[normalizedLocale.split('-')[0]] || 'en'
  dayjs.locale(dayjsLocale)
  return dayjsLocale
}

export default dayjs
