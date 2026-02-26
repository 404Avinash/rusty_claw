html = open('web/index_template.html', encoding='utf-8').read()
open('web/index.html', 'w', encoding='utf-8').write(html)
print('done')
