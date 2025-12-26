export const endpoints = {
  vacancies: {
    list: 'vacancies_parser/headhunter/vacancies/',
    detail: id => `vacancies_parser/headhunter/vacancies/${id}/`,
    stats: 'vacancies_parser/headhunter/vacancies/stats/',
    versions: id => `vacancies_parser/headhunter/vacancies/${id}/versions/`,
    versionDetail: id => `vacancies_parser/headhunter/vacancies/${id}/version_detail/`,
    changes: id => `vacancies_parser/headhunter/vacancies/${id}/changes/`,
    parseSingle: 'vacancies_parser/headhunter/vacancies/parse_single/',
    taskStatus: 'vacancies_parser/headhunter/vacancies/task_status/'
  },
  parsing: {
    parseByRoles: 'vacancies_parser/headhunter/parsing/parse_by_roles/',
    parseByTechnologies: 'vacancies_parser/headhunter/parsing/parse_by_technologies/'
  }
}

