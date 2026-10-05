"""Read-only cloud/local UI checks. Synthetic fixtures processed inside the browser only."""
import argparse,base64,json,time
from pathlib import Path
from zipfile import ZipFile
import fitz
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait,Select

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--skip-game',action='store_true');args=parser.parse_args()
site='https://carbon-eye-sip.netlify.app' if args.live else 'http://127.0.0.1:5176'
output=ROOT/'outputs/creation-tools'/('live' if args.live else 'local');output.mkdir(parents=True,exist_ok=True)
options=Options()
for flag in ['--headless=new','--window-size=1440,1100','--enable-unsafe-swiftshader']:options.add_argument(flag)
driver=webdriver.Edge(service=Service(str(ROOT/'outputs/human3/webdriver-cache/msedgedriver/win64/154.0.4258.53/msedgedriver.exe')),options=options)
driver.execute_cdp_cmd('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument',{'source':"const original=window.fetch;window.__writeCalls=[];window.fetch=(u,o={})=>{if(o.method&&!['GET','HEAD'].includes(o.method.toUpperCase()))window.__writeCalls.push({url:String(u),method:o.method});return original(u,o)};"})
checks=[]
def wait(fn,timeout=45):return WebDriverWait(driver,timeout,poll_frequency=.1).until(fn)
def element(selector):return wait(lambda d:next((e for e in d.find_elements('css selector',selector) if e.is_displayed()),None))
def button(text):return wait(lambda d:next((e for e in d.find_elements('tag name','button') if e.is_displayed() and e.text.strip()==text),None))
def click(e):driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})",e);e.click()
def visit(path,selector):driver.get(site+path);element(selector)
def overflow():assert driver.execute_script('return document.documentElement.scrollWidth<=innerWidth'),'horizontal overflow'
def download_blob(path):
    link=element('.download-file');driver.set_script_timeout(35)
    data=driver.execute_async_script("const done=arguments[arguments.length-1];fetch(arguments[0]).then(r=>r.blob()).then(blob=>{const r=new FileReader();r.onload=()=>done(r.result.split(',')[1]);r.readAsDataURL(blob)}).catch(()=>done(null))",link.get_attribute('href'))
    assert data;target=output/path;target.write_bytes(base64.b64decode(data));return target
def file_input(path):driver.find_element('css selector','input[type=file]').send_keys(str(path.resolve()))
def ready_preview():return wait(lambda d:d.find_elements('css selector','.document-result') or d.find_elements('css selector','.convert-error'))
try:
    visit('/crypto-lab','.algorithm-tabs');click(button('计算并生成轨迹'));assert '69c4e0d86a7b0430d8cdb78070b4c55a' in element('.trace-result output').text
    assert len(driver.find_elements('css selector','.state-matrix>div'))==16
    click(button('下一步 →'));assert 'AddRoundKey' in element('.trace-panel h3').text
    driver.execute_script("arguments[0].value=11;arguments[0].dispatchEvent(new Event('input',{bubbles:true}))",element('.trace-range input'))
    assert 'MixColumns' in element('.trace-panel h3').text or '轮' in element('.trace-panel h3').text
    field=element('.lab-inputs textarea');field.send_keys('0');assert not driver.find_elements('css selector','.trace-panel');click(button('计算并生成轨迹'));element('.lab-error')
    checks.append('AES actual state matrix, known-vector output, scrubbing and stale-result invalidation')
    for ident,result in [('sha','ba7816bf8f01cfea'),('rsa','2790'),('dh','Alice = 2'),('caesar','Khoor'),('vigenere','LXFOPV'),('xor','')]:
        click(driver.find_element('css selector',f'.algorithm-tabs button:nth-child({["aes","sha","rsa","dh","caesar","vigenere","xor"].index(ident)+1})'));click(button('计算并生成轨迹'));assert result in element('.trace-result output').text;assert driver.find_elements('css selector','.principle-diagram .diagram-node')
    click(driver.find_element('css selector','.algorithm-tabs button:nth-child(2)'));click(button('计算并生成轨迹'));click(button('自动播放'));wait(lambda d:'2 /' in element('.trace-range').text);click(button('暂停'));assert not driver.execute_script('return window.__writeCalls.length')
    driver.save_screenshot(str(output/'crypto-desktop.png'));checks.append('seven algorithms, live trace playback and principles; no cloud requests or retained input')
    visit('/document-tools','.document-drop');file_input(ROOT/'frontend/node_modules/mammoth/test/test-data/tables.docx');click(button('生成预览'));ready_preview();assert not driver.find_elements('css selector','.convert-error'),element('.convert-error').text if driver.find_elements('css selector','.convert-error') else ''
    assert driver.find_elements('css selector','.word-preview table');assert not driver.find_elements('css selector','.word-preview script,.word-preview a')
    driver.save_screenshot(str(output/'word-preview.png'));click(button('生成 PDF 下载文件'));element('.download-file');pdf_path=download_blob('word-output.pdf')
    pdf=fitz.open(pdf_path);assert 1<=len(pdf)<=12
    for i,page in enumerate(pdf):page.get_pixmap(matrix=fitz.Matrix(1.1,1.1)).save(output/f'word-pdf-page-{i+1}.png')
    pdf.close();checks.append('real DOCX table fixture converted to preview and structurally valid raster PDF')
    # Feeding the generated raster PDF back into editable mode must explain missing OCR honestly.
    file_input(pdf_path);click(button('生成预览'));element('.convert-error');assert 'OCR' in element('.convert-error').text
    Select(element('.convert-settings select')).select_by_value('appearance');click(button('生成预览'));ready_preview();assert driver.find_elements('css selector','.pdf-pages img');click(button('生成 Word 下载文件'));element('.download-file');appearance=download_blob('appearance.docx')
    with ZipFile(appearance) as archive:assert any(name.startswith('word/media/') for name in archive.namelist());assert b'<w:sectPr' in archive.read('word/document.xml')
    checks.append('scanned/raster PDF has no fabricated editable text; appearance mode embeds actual page image')
    file_input(ROOT/'outputs/creation-tools/two-pages.pdf');Select(element('.convert-settings select')).select_by_value('editable');click(button('生成预览'));ready_preview();assert len(driver.find_elements('css selector','.pdf-pages textarea'))==2;assert 'Editable original text' in element('.pdf-pages textarea').get_attribute('value')
    click(button('生成 Word 下载文件'));element('.download-file');editable=download_blob('editable.docx')
    with ZipFile(editable) as archive:assert b'Editable original text' in archive.read('word/document.xml');assert archive.read('word/document.xml').count(b'<w:sectPr')==2
    element('.pdf-pages textarea').send_keys('\n中文转换测试：基地建设与生存。\n'+ '\n'.join(f'第 {i+1} 行：资料仅在本地转换，检查中文、段落和跨页。' for i in range(40)));assert not driver.find_elements('css selector','.download-file')
    click(button('生成 Word 下载文件'));element('.download-file');chinese=download_blob('chinese-edited.docx')
    with ZipFile(chinese) as archive:assert '中文转换测试'.encode() in archive.read('word/document.xml')
    file_input(chinese);click(button('生成预览'));ready_preview();assert '中文转换测试' in element('.word-preview').text
    click(button('生成 PDF 下载文件'));element('.download-file');long_pdf=download_blob('chinese-multipage.pdf')
    with fitz.open(long_pdf) as document:
        assert 2<=len(document)<=12
        for i,page in enumerate(document):page.get_pixmap(matrix=fitz.Matrix(1,1)).save(output/f'chinese-pdf-page-{i+1}.png')
    checks.append('actual edited Chinese DOCX round-trip and multi-page PDF, every output PDF page rendered for visual QA')
    click(button('清除文件与结果'));assert not driver.find_elements('css selector','.document-result,.download-file');assert not driver.execute_script('return window.__writeCalls.length')
    checks.append('two-page text PDF becomes editable DOCX; edits revoke stale output; clearing releases preview and URLs')
    if not args.skip_game:
        visit('/wasteland','.camp-stage canvas');click(button('开始建设'))
        for kind in ['garden','water','generator','turret']:
            click(element(f'[data-building={kind}]'));click(button('确认建造'))
        wait(lambda d:int(element('.camp-stage').get_attribute('data-buildings'))==5);assert element('[data-resource=wood]').text=='4';assert '2 / 3' in element('.camp-resources').text
        click(button('取消建造 ×'));driver.execute_script('arguments[0].focus({preventScroll:true})',element('.camp-stage'));before=element('.camp-stage').get_attribute('data-x')
        ActionChains(driver).key_down('a').pause(.4).key_up('a').perform();assert before!=element('.camp-stage').get_attribute('data-x')
        click(button('放大营地'));element('.camp-stage.is-expanded');ActionChains(driver).send_keys(Keys.ESCAPE).perform();assert not driver.find_elements('css selector','.camp-stage.is-expanded');wait(lambda d:element('.camp-stage').get_attribute('data-phase')=='paused');assert driver.execute_script('return document.body.style.overflow')!='hidden'
        cycle=element('.camp-stage').get_attribute('data-cycle');time.sleep(.25);assert cycle==element('.camp-stage').get_attribute('data-cycle');click(button('继续营地'))
        driver.save_screenshot(str(output/'camp-desktop.png'));checks.append('actual construction costs, power capacity, keyboard movement, pause and expansion cleanup')
        for day in [1,2,3]:
            click(button('准备好了，迎接夜晚'));driver.execute_script('arguments[0].focus({preventScroll:true})',element('.camp-stage'));ActionChains(driver).key_down(Keys.SPACE).perform()
            wait(lambda d:d.find_elements('css selector','.camp-upgrades button') or element('.camp-stage').get_attribute('data-phase') in ['won','lost'],120)
            ActionChains(driver).key_up(Keys.SPACE).perform();assert element('.camp-stage').get_attribute('data-phase')!='lost','camp lost during real three-night journey'
            if day<3:click(element('.camp-upgrades button:nth-child(2)'))
        assert element('.camp-stage').get_attribute('data-phase')=='won';assert int(element('.camp-stage').get_attribute('data-kills'))==24
        checks.append('complete three-night survival through actual UI and real defense key, no teleport/time mutation/resource injection')
    for width in [390,320]:
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':width,'height':844,'deviceScaleFactor':1,'mobile':True})
        for path,selector in [('/document-tools','.document-drop'),('/crypto-lab','.algorithm-tabs'),('/wasteland','.camp-stage canvas')]:visit(path,selector);overflow()
        click(button('开始建设'));click(element('[data-building=garden]'));click(button('确认建造'));overflow();driver.save_screenshot(str(output/f'camp-mobile-{width}.png'))
    checks.append('all three new pages fit 390px and 320px; mobile building controls actually place a structure')
    assert not driver.execute_script('return window.__writeCalls.length')
    result={'status':'passed','count':len(checks),'checks':checks,'cloud_writes':False,'actual_model_calls':0};(output/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
except Exception:
    driver.save_screenshot(str(output/'failure.png'));raise
finally:driver.quit()
