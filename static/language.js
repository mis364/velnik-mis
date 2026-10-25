(() => {
  const translations = new Map(Object.entries({
    'Main navigation': 'मुख्य नेविगेशन',
    Snapshot: 'स्नैपशॉट',
    'Period comparison': 'अवधि तुलना',
    'Year-over-year': 'वर्ष-दर-वर्ष',
    'State billing': 'राज्य बिक्री',
    Weekly: 'साप्ताहिक',
    Nepal: 'नेपाल',
    Analysis: 'विश्लेषण',
    'Local analysis': 'स्थानीय विश्लेषण',
    Products: 'उत्पाद',
    Distributors: 'वितरक',
    'Stock report': 'स्टॉक रिपोर्ट',
    'Billing efficiency': 'बिलिंग दक्षता',
    Summary: 'सारांश',
    'Monthly trend': 'मासिक रुझान',
    'State / zone': 'राज्य / ज़ोन',
    Representatives: 'प्रतिनिधि',
    'Zero billing': 'शून्य बिलिंग',
    'Daily upload': 'दैनिक अपलोड',
    'Download backup': 'बैकअप डाउनलोड करें',
    'Sign out': 'साइन आउट',
    'Sales report': 'बिक्री रिपोर्ट',
    'Stock summary': 'स्टॉक सारांश',
    'VELNIK MIS': 'VELNIK MIS',
    'Workbook loaded': 'वर्कबुक लोड हुई',
    'Stock workbook not loaded': 'स्टॉक वर्कबुक लोड नहीं हुई',
    'Billing workbook not loaded': 'बिलिंग वर्कबुक लोड नहीं हुई',
    'DISTRIBUTOR · BILLING MIS': 'वितरक · बिलिंग MIS',
    'Monthly billing coverage, state and representative performance, product reach, and active distributors to follow up.': 'मासिक बिलिंग कवरेज, राज्य और प्रतिनिधि प्रदर्शन, उत्पाद पहुँच और अनुवर्ती कार्रवाई वाले सक्रिय वितरक।',
    'FINANCIAL YEAR': 'वित्तीय वर्ष',
    'Upload billing efficiency workbook': 'बिलिंग दक्षता वर्कबुक अपलोड करें',
    'Choose the .xlsm or .xlsx workbook containing an': '.xlsm या .xlsx वर्कबुक चुनें जिसमें',
    'sheet with headers on row 2.': 'शीट की हेडर पंक्ति 2 पर हो।',
    'This workbook is stored separately from sales and stock data. Macros are not run.': 'यह वर्कबुक बिक्री और स्टॉक डेटा से अलग रखी जाती है। मैक्रो नहीं चलाए जाते।',
    'Current source: —': 'वर्तमान स्रोत: —',
    'Choose billing workbook': 'बिलिंग वर्कबुक चुनें',
    'Billing efficiency workbook uploads are managed by the owner.': 'बिलिंग दक्षता वर्कबुक अपलोड का प्रबंधन मालिक करता है।',
    'Upload a billing efficiency workbook to build this report': 'यह रिपोर्ट बनाने के लिए बिलिंग दक्षता वर्कबुक अपलोड करें',
    'The owner can upload the separate billing workbook. Existing sales and stock reports will not be changed.': 'मालिक अलग बिलिंग वर्कबुक अपलोड कर सकता है। मौजूदा बिक्री और स्टॉक रिपोर्ट नहीं बदलेंगी।',
    Month: 'महीना',
    'Billing coverage by month': 'महीने के अनुसार बिलिंग कवरेज',
    'Efficiency is active distributors with positive Value In Lacs divided by active distributor codes.': 'दक्षता = सकारात्मक Value In Lacs वाले सक्रिय वितरक ÷ सक्रिय वितरक कोड।',
    'Sales (lakh)': 'बिक्री (लाख)',
    'Active DBs': 'सक्रिय DB',
    'Billed active DBs': 'बिलिंग वाले सक्रिय DB',
    'Active zero billing': 'शून्य बिलिंग वाले सक्रिय DB',
    Efficiency: 'दक्षता',
    'Selected month breakdown.': 'चयनित महीने का विवरण।',
    'Ranked by sales value': 'बिक्री राशि के अनुसार क्रमबद्ध',
    Zone: 'ज़ोन',
    'FIELD TEAM': 'फील्ड टीम',
    'Representative performance': 'प्रतिनिधि प्रदर्शन',
    'Based on the workbook’s Res SR/SO Name field for the selected month.': 'चयनित महीने के लिए वर्कबुक के Res SR/SO Name फ़ील्ड पर आधारित।',
    Representative: 'प्रतिनिधि',
    'Zero billing DBs': 'शून्य बिलिंग वाले DB',
    'PRODUCT REACH': 'उत्पाद पहुँच',
    'Product billing coverage': 'उत्पाद बिलिंग कवरेज',
    'Counts active distributors with a positive value in each product column. Values themselves are not shown because the workbook does not specify their unit.': 'हर उत्पाद कॉलम में सकारात्मक मान वाले सक्रिय वितरकों की संख्या। मान की इकाई वर्कबुक में नहीं दी गई, इसलिए मान नहीं दिखाए गए।',
    Product: 'उत्पाद',
    'Active DBs billed': 'बिलिंग वाले सक्रिय DB',
    'Active DB coverage': 'सक्रिय DB कवरेज',
    'Active distributors without positive billing': 'सकारात्मक बिलिंग के बिना सक्रिय वितरक',
    'Confirm the selected month’s zero or negative net billing before follow-up.': 'अनुवर्ती कार्रवाई से पहले चयनित महीने की शून्य या ऋणात्मक शुद्ध बिलिंग की पुष्टि करें।',
    'Download zero-billing CSV': 'शून्य-बिलिंग CSV डाउनलोड करें',
    'Search name, code, state, or representative': 'नाम, कोड, राज्य या प्रतिनिधि खोजें',
    'Type to search': 'खोजने के लिए लिखें',
    'All states / regions': 'सभी राज्य / क्षेत्र',
    'DB code': 'DB कोड',
    Distributor: 'वितरक',
    'Super stockist': 'सुपर स्टॉकिस्ट',
    Previous: 'पिछला',
    Next: 'अगला',
    'ASD and ASDF are present in the source workbook but are not interpreted because their meanings are not defined. Product coverage is based only on positive product-column values. Duplicate distributor-month rows are flagged; sales values from duplicate rows are included in totals.': 'स्रोत वर्कबुक में ASD और ASDF हैं, पर अर्थ स्पष्ट नहीं होने के कारण उनकी व्याख्या नहीं की गई। उत्पाद कवरेज केवल सकारात्मक उत्पाद-कॉलम मानों पर आधारित है। डुप्लिकेट वितरक-महीना पंक्तियाँ चिह्नित हैं; उनकी बिक्री राशि कुल में शामिल है।',
    'Billing analysis is calculated from the uploaded workbook. Verify figures and distributor status against the source before taking action.': 'बिलिंग विश्लेषण अपलोड की गई वर्कबुक से निकाला गया है। कार्रवाई से पहले आँकड़ों और वितरक स्थिति की स्रोत से पुष्टि करें।',
    'REPORT PERIOD': 'रिपोर्ट अवधि',
    'Latest workbook loaded: —': 'नवीनतम वर्कबुक लोड: —',
    'Latest workbook: —': 'नवीनतम वर्कबुक: —',
    'SALES PERFORMANCE · MIS': 'बिक्री प्रदर्शन · MIS',
    'Sales overview': 'बिक्री का सारांश',
    'Daily movement, plan gaps, product mix, and distributors to follow up.': 'दैनिक गतिविधि, योजना का अंतर, उत्पाद मिश्रण और अनुवर्ती कार्रवाई वाले वितरक।',
    'DAILY WORKBOOK': 'दैनिक वर्कबुक',
    "Upload today's sales workbook": 'आज की बिक्री वर्कबुक अपलोड करें',
    'The latest uploaded workbook is shown automatically when you open this page. Upload today\'s .xlsx file to refresh the report.': 'इस पेज को खोलने पर नवीनतम अपलोड की गई वर्कबुक अपने-आप दिखाई जाती है। रिपोर्ट अपडेट करने के लिए आज की .xlsx फ़ाइल अपलोड करें।',
    'Refresh from Excel': 'Excel से अपडेट करें',
    'Choose an .xlsx file with the': 'ऐसी .xlsx फ़ाइल चुनें जिसमें',
    'sheets. The': 'शीट हों।',
    'sheet adds plan-gap analysis.': 'शीट योजना-अंतर विश्लेषण जोड़ती है।',
    'On Render\'s free service, uploaded files may be lost after a restart or redeploy. Check the workbook name and upload time below; download a backup before planned restarts.': 'Render की निःशुल्क सेवा में रीस्टार्ट या पुनः डिप्लॉय के बाद अपलोड की गई फ़ाइलें खो सकती हैं। नीचे वर्कबुक का नाम और अपलोड समय देखें; नियोजित रीस्टार्ट से पहले बैकअप डाउनलोड करें।',
    'Choose workbook': 'वर्कबुक चुनें',
    'Workbook uploads are managed by the owner. The report below uses the latest workbook currently available on the service.': 'वर्कबुक अपलोड का प्रबंधन मालिक करता है। नीचे की रिपोर्ट सेवा पर उपलब्ध नवीनतम वर्कबुक का उपयोग करती है।',
    'LOCAL · BUSINESS ANALYST': 'स्थानीय · व्यवसाय विश्लेषण',
    'Ask about sales and stock': 'बिक्री और स्टॉक के बारे में पूछें',
    'Get data-based trends, risks, and practical follow-up ideas without API credits.': 'API क्रेडिट के बिना डेटा-आधारित रुझान, जोखिम और व्यावहारिक अनुवर्ती सुझाव पाएँ।',
    'Analysis runs on this computer using fixed report checks. No workbook data or API key is sent online. This local analyst is not a generative AI model.': 'विश्लेषण इस कंप्यूटर पर निर्धारित रिपोर्ट जाँचों के आधार पर चलता है। वर्कबुक डेटा या API कुंजी ऑनलाइन नहीं भेजी जाती। यह स्थानीय विश्लेषक जनरेटिव AI मॉडल नहीं है।',
    'Ask about sales trends, plan gaps, product performance, stock risks, or data checks.': 'बिक्री के रुझान, योजना-अंतर, उत्पाद प्रदर्शन, स्टॉक जोखिम या डेटा जाँच के बारे में पूछें।',
    'Ask about stock risks, inventory leaders, sales trends, plan gaps, or data checks.': 'स्टॉक जोखिम, अधिक स्टॉक वाले उत्पाद, बिक्री रुझान, योजना-अंतर या डेटा जाँच के बारे में पूछें।',
    Analyze: 'विश्लेषण करें',
    'Sales + stock': 'बिक्री + स्टॉक',
    'Sales only': 'केवल बिक्री',
    'Stock only': 'केवल स्टॉक',
    'Your question': 'आपका प्रश्न',
    'Which states have high stock but low billing?': 'किन राज्यों में स्टॉक अधिक और बिक्री कम है?',
    'Download action report': 'कार्रवाई रिपोर्ट डाउनलोड करें',
    'PERIOD · COMPARISON': 'अवधि · तुलना',
    'Current vs previous period': 'वर्तमान बनाम पिछली अवधि',
    'Compare equal-length date ranges and identify state-level changes.': 'समान अवधि की तारीखों की तुलना करें और राज्य-स्तरीय बदलाव पहचानें।',
    'State / region': 'राज्य / क्षेत्र',
    'Previous sales (lakh)': 'पिछली बिक्री (लाख)',
    'Current sales (lakh)': 'वर्तमान बिक्री (लाख)',
    'Change (lakh)': 'बदलाव (लाख)',
    'Change %': 'बदलाव %',
    'Comparison uses dated Raw sales without GST and excludes manual Nepal summary amounts. The preceding period must be covered by dates in the uploaded sales workbook. Percentage change is not shown when prior-period sales are zero.': 'तुलना Raw शीट की तारीख़ वाली GST-रहित बिक्री पर आधारित है और नेपाल की मैन्युअल सारांश राशि शामिल नहीं करती। अपलोड की गई बिक्री वर्कबुक में पिछली अवधि की तारीख़ें होनी चाहिए। पिछली अवधि की बिक्री शून्य होने पर प्रतिशत बदलाव नहीं दिखाया जाता।',
    'YEAR · COMPARISON': 'वर्ष · तुलना',
    'Compare with last year': 'पिछले वर्ष से तुलना करें',
    'Upload the separate prior-year sales workbook to compare matching calendar dates.': 'समान कैलेंडर तारीख़ों की तुलना के लिए पिछले वर्ष की बिक्री वर्कबुक अलग से अपलोड करें।',
    'Last-year sales workbook': 'पिछले वर्ष की बिक्री वर्कबुक',
    'Choose your FY 2025–26 sales workbook. This is stored separately and will not replace the current sales workbook.': 'FY 2025–26 की बिक्री वर्कबुक चुनें। यह अलग से सहेजी जाएगी और वर्तमान बिक्री वर्कबुक को नहीं बदलेगी।',
    'No last-year workbook uploaded.': 'पिछले वर्ष की वर्कबुक अपलोड नहीं हुई।',
    'Choose last-year workbook': 'पिछले वर्ष की वर्कबुक चुनें',
    'Last-year workbooks are managed by the owner.': 'पिछले वर्ष की वर्कबुक का प्रबंधन मालिक करता है।',
    'Last year (lakh)': 'पिछला वर्ष (लाख)',
    'Current year (lakh)': 'वर्तमान वर्ष (लाख)',
    'Uses dated Raw sales without GST and compares matching dates one year apart. Manual summary-sheet amounts are excluded. The uploaded workbook must cover the full matching prior-year range.': 'यह तारीख़ वाली Raw शीट की GST-रहित बिक्री से एक वर्ष के अंतर वाली समान तारीख़ों की तुलना करता है। मैन्युअल सारांश शीट की राशि शामिल नहीं है। अपलोड की गई वर्कबुक में पिछले वर्ष की पूरी मिलान अवधि होनी चाहिए।',
    '01 · DAILY SALES': '01 · दैनिक बिक्री',
    'Sales snapshot': 'बिक्री सारांश',
    'Amounts without GST unless a card says “with tax”.': 'जब तक कार्ड पर “कर सहित” न लिखा हो, सभी राशि GST-रहित हैं।',
    From: 'से',
    To: 'तक',
    'Update view': 'दृश्य अपडेट करें',
    'Sales by day': 'दिन के अनुसार बिक्री',
    'Daily sales in lakh': 'दैनिक बिक्री (लाख में)',
    LAKH: 'लाख',
    'STATE · BILLING': 'राज्य · बिक्री',
    'Billing by state / region for the selected date range.': 'चुनी गई तारीख़ अवधि में राज्य / क्षेत्र के अनुसार बिक्री।',
    'Billing by state / region': 'राज्य / क्षेत्र के अनुसार बिक्री',
    'Ranked by billed sales, highest first': 'बिक्री राशि के अनुसार, सबसे अधिक पहले',
    'State billing ranking': 'राज्य बिक्री क्रम',
    'Billing rank follows billed amount; per-capita rank compares billing per resident. Ties share a rank.': 'बिक्री क्रम बिक्री राशि के अनुसार है; प्रति व्यक्ति क्रम प्रति निवासी बिक्री की तुलना करता है। बराबरी पर समान क्रम दिया जाता है।',
    'Billing rank': 'बिक्री क्रम',
    Billing: 'बिक्री',
    'Per-capita rank': 'प्रति व्यक्ति क्रम',
    'Population est.': 'अनुमानित जनसंख्या',
    'Billing / person': 'प्रति व्यक्ति बिक्री',
    Share: 'हिस्सा',
    'Per-capita billing uses the projected population estimate for 1 July 2026. SO combines AP, TG, KR, KN, and TN; MH combines its component regions when present, otherwise the MH total. Nessa is treated as the Northeast group. Nepal and regions without population estimates are not per-capita ranked. Source:': 'प्रति व्यक्ति बिक्री में 1 जुलाई 2026 की अनुमानित जनसंख्या का उपयोग किया गया है। SO में AP, TG, KR, KN और TN शामिल हैं; MH के घटक क्षेत्र उपलब्ध होने पर उन्हें, अन्यथा MH कुल को जोड़ा जाता है। Nessa को पूर्वोत्तर समूह माना गया है। नेपाल और बिना जनसंख्या अनुमान वाले क्षेत्रों की प्रति व्यक्ति रैंक नहीं है। स्रोत:',
    'source report': 'स्रोत रिपोर्ट',
    'WEEKLY · STATE PERFORMANCE': 'साप्ताहिक · राज्य प्रदर्शन',
    'Week-wise performance': 'सप्ताह के अनुसार प्रदर्शन',
    'Weekly plan and achievement by state from the planning workbook.': 'योजना वर्कबुक से राज्यवार साप्ताहिक लक्ष्य और उपलब्धि।',
    'Weekly plan workbook': 'साप्ताहिक योजना वर्कबुक',
    'Upload an .xlsx workbook with': 'ऐसी .xlsx वर्कबुक अपलोड करें जिसमें',
    'columns on the first sheet.': 'कॉलम पहली शीट पर हों।',
    'Choose weekly plan': 'साप्ताहिक योजना चुनें',
    'Weekly plan workbooks are managed by the owner.': 'साप्ताहिक योजना वर्कबुक का प्रबंधन मालिक करता है।',
    'No weekly plan is loaded.': 'कोई साप्ताहिक योजना लोड नहीं है।',
    'Weekly performance by state / region': 'राज्य / क्षेत्र के अनुसार साप्ताहिक प्रदर्शन',
    'Weekly data checks': 'साप्ताहिक डेटा जाँच',
    'Values are taken from the weekly planning workbook.': 'आँकड़े साप्ताहिक योजना वर्कबुक से लिए गए हैं।',
    'Week plan': 'साप्ताहिक लक्ष्य',
    'Week achievement': 'साप्ताहिक उपलब्धि',
    'Achievement': 'उपलब्धि',
    Balance: 'शेष',
    'NEPAL · MANUAL SUMMARY': 'नेपाल · मैन्युअल सारांश',
    'Nepal sales': 'नेपाल बिक्री',
    'Nepal figures from the Without GST summary sheet, shown separately from transaction dates.': 'GST-रहित सारांश शीट के नेपाल आँकड़े लेन-देन की तारीख़ों से अलग दिखाए गए हैं।',
    '02 · WHERE TO IMPROVE': '02 · सुधार के अवसर',
    'Action points from the data': 'डेटा से कार्रवाई के सुझाव',
    'These are areas to review; the workbook alone cannot explain the cause.': 'इन क्षेत्रों की समीक्षा करें; केवल वर्कबुक से कारण स्पष्ट नहीं हो सकता।',
    'State / region plan progress': 'राज्य / क्षेत्र योजना प्रगति',
    'Plan, achievement, and remaining gap from the workbook.': 'वर्कबुक से लक्ष्य, उपलब्धि और शेष अंतर।',
    Plan: 'लक्ष्य',
    Achieved: 'प्राप्त',
    Achievement: 'उपलब्धि',
    'Gap to plan': 'लक्ष्य से अंतर',
    '03 · PRODUCT MIX': '03 · उत्पाद मिश्रण',
    'Product mix report': 'उत्पाद मिश्रण रिपोर्ट',
    'Ranked by sales without GST for the selected date range.': 'चुनी गई तारीख़ अवधि की GST-रहित बिक्री के अनुसार क्रमबद्ध।',
    'Product sales chart': 'उत्पाद बिक्री चार्ट',
    '04 · FOLLOW UP': '04 · अनुवर्ती कार्रवाई',
    'Active distributors with zero billing': 'शून्य बिक्री वाले सक्रिय वितरक',
    'From the workbook’s “Zero Billing DB” flag. Confirm with the representative before acting.': 'वर्कबुक के “Zero Billing DB” संकेत पर आधारित। कार्रवाई से पहले प्रतिनिधि से पुष्टि करें।',
    'Search distributor, code, or representative': 'वितरक, कोड या प्रतिनिधि खोजें',
    'Type to search': 'खोजने के लिए लिखें',
    'All states / regions': 'सभी राज्य / क्षेत्र',
    Representative: 'प्रतिनिधि',
    'All representatives': 'सभी प्रतिनिधि',
    'Download CSV': 'CSV डाउनलोड करें',
    Distributor: 'वितरक',
    'DB code': 'DB कोड',
    'Sales representative': 'बिक्री प्रतिनिधि',
    'Area manager': 'क्षेत्र प्रबंधक',
    'Super stockist': 'सुपर स्टॉकिस्ट',
    Previous: 'पिछला',
    Next: 'अगला',
    'Owner sign in': 'मालिक साइन इन',
    'Sales values are in lakh. “With tax” and “Without GST” are separate source measures. This report is for review; confirm unusual values with the source team.': 'बिक्री राशि लाख में है। “कर सहित” और “GST-रहित” अलग स्रोत माप हैं। यह रिपोर्ट समीक्षा के लिए है; असामान्य आँकड़ों की स्रोत टीम से पुष्टि करें।',
    'STOCK AS OF': 'स्टॉक की तारीख़',
    'INVENTORY · STOCK MIS': 'इन्वेंटरी · स्टॉक MIS',
    'Product and state stock, distributor balances, and negative-stock checks.': 'उत्पाद और राज्य का स्टॉक, वितरक शेष और नकारात्मक स्टॉक जाँच।',
    'Upload stock workbook': 'स्टॉक वर्कबुक अपलोड करें',
    'Choose the stock report Excel file. It is saved separately from the sales workbook.': 'स्टॉक रिपोर्ट की Excel फ़ाइल चुनें। यह बिक्री वर्कबुक से अलग सहेजी जाती है।',
    'Required sheets: Stock, Item Stock CS & SS Stock, and State wise Stock. Values are displayed as recorded in the workbook.': 'आवश्यक शीट: Stock, Item Stock CS & SS Stock और State wise Stock। आँकड़े वर्कबुक के अनुसार दिखाए जाते हैं।',
    'No stock workbook loaded yet.': 'अभी कोई स्टॉक वर्कबुक लोड नहीं है।',
    'Choose stock workbook': 'स्टॉक वर्कबुक चुनें',
    'Stock workbook uploads are managed by the owner.': 'स्टॉक वर्कबुक अपलोड का प्रबंधन मालिक करता है।',
    'Upload a stock workbook to build this report': 'यह रिपोर्ट बनाने के लिए स्टॉक वर्कबुक अपलोड करें',
    'The stock report is not available yet. The owner can sign in to upload a stock workbook.': 'स्टॉक रिपोर्ट अभी उपलब्ध नहीं है। मालिक साइन इन करके स्टॉक वर्कबुक अपलोड कर सकता है।',
    'Key stock figures': 'स्टॉक के मुख्य आँकड़े',
    '01 · STOCK MIX': '01 · स्टॉक मिश्रण',
    'Stock by product': 'उत्पाद के अनुसार स्टॉक',
    'CS and SS balances and negative stock from the workbook.': 'वर्कबुक से CS और SS शेष तथा नकारात्मक स्टॉक।',
    'WORKBOOK VALUE': 'वर्कबुक मान',
    'Highest stock by product': 'उत्पाद के अनुसार सबसे अधिक स्टॉक',
    'Top 10 items by total stock': 'कुल स्टॉक के अनुसार शीर्ष 10 आइटम',
    'Stock by state / region': 'राज्य / क्षेत्र के अनुसार स्टॉक',
    'Totals summed from the State wise Stock sheet': 'State wise Stock शीट से जोड़े गए कुल आँकड़े',
    'Product stock details': 'उत्पाद स्टॉक विवरण',
    'NPD stock is shown separately in the summary and is not added to this item total.': 'NPD स्टॉक सारांश में अलग दिखाया गया है और इस आइटम के कुल में नहीं जोड़ा गया है।',
    Product: 'उत्पाद',
    CS: 'CS',
    SS: 'SS',
    Total: 'कुल',
    'Negative stock': 'नकारात्मक स्टॉक',
    '02 · DISTRIBUTOR BALANCES': '02 · वितरक शेष',
    'Stock by distributor': 'वितरक के अनुसार स्टॉक',
    'Select a state to download every product row from the uploaded State wise Stock sheet.': 'अपलोड की गई State wise Stock शीट से सभी उत्पाद पंक्तियाँ डाउनलोड करने के लिए राज्य चुनें।',
    'Search name or state': 'नाम या राज्य खोजें',
    'Download state stock CSV': 'राज्य स्टॉक CSV डाउनलोड करें',
    Type: 'प्रकार',
    'Distributor / stock point': 'वितरक / स्टॉक पॉइंट',
    'Total stock': 'कुल स्टॉक',
    'Negative items': 'नकारात्मक आइटम',
    'Stock figures are shown as provided in the uploaded workbook. Verify stock balances against the source before taking action.': 'स्टॉक आँकड़े अपलोड की गई वर्कबुक के अनुसार दिखाए गए हैं। कार्रवाई से पहले स्रोत से स्टॉक शेष की पुष्टि करें।',
    'LAKH · ₹ / PERSON': 'लाख · ₹ / व्यक्ति',
    'Data checks': 'डेटा जाँच',
    'Billing on': 'की बिक्री',
    'Today\'s achievement': 'आज की उपलब्धि',
    'No figures are available.': 'कोई आँकड़े उपलब्ध नहीं हैं।',
    'No figures are available for this selection.': 'इस चयन के लिए कोई आँकड़े उपलब्ध नहीं हैं।',
    'Previous-period data is unavailable.': 'पिछली अवधि का डेटा उपलब्ध नहीं है।',
    'No state/region billing is available in these periods.': 'इन अवधियों के लिए राज्य / क्षेत्र बिक्री उपलब्ध नहीं है।',
    'Last-year sales data is not loaded.': 'पिछले वर्ष की बिक्री का डेटा लोड नहीं है।',
    'Matching prior-year dates are unavailable.': 'पिछले वर्ष की समान तारीख़ें उपलब्ध नहीं हैं।',
    'No percentage baseline (previous sales were zero)': 'प्रतिशत तुलना उपलब्ध नहीं (पिछली बिक्री शून्य थी)',
    'No percentage baseline (last-year sales were zero)': 'प्रतिशत तुलना उपलब्ध नहीं (पिछले वर्ष की बिक्री शून्य थी)',
    'Previous period sales': 'पिछली अवधि की बिक्री',
    'Selected period sales': 'चुनी अवधि की बिक्री',
    'Last-year sales': 'पिछले वर्ष की बिक्री',
    'Current-year sales': 'वर्तमान वर्ष की बिक्री',
    Change: 'बदलाव',
    'Without GST': 'GST-रहित',
    'With tax': 'कर सहित',
    'Selected-period sales': 'चुनी अवधि की बिक्री',
    'Active zero-billing distributors': 'शून्य बिक्री वाले सक्रिय वितरक',
    'Missing net values': 'शुद्ध राशि अनुपलब्ध',
    'Flagged in the source workbook': 'स्रोत वर्कबुक में चिह्नित',
    'No sales in the selected dates.': 'चुनी गई तारीख़ों में बिक्री नहीं है।',
    'No state plan data found in the Without GST sheet.': 'GST-रहित शीट में राज्य योजना डेटा नहीं मिला।',
    'No NP summary row was found in the Without GST sheet.': 'GST-रहित शीट में NP सारांश पंक्ति नहीं मिली।',
    'Update Nepal figures': 'नेपाल के आँकड़े अपडेट करें',
    'Enter amounts in lakh. Saving updates the report for this reporting month.': 'राशि लाख में दर्ज करें। सहेजने पर इस रिपोर्टिंग माह की रिपोर्ट अपडेट होगी।',
    'Monthly plan': 'मासिक लक्ष्य',
    'Monthly billing achievement': 'मासिक बिक्री उपलब्धि',
    'Billing on summary date': 'सारांश तारीख़ की बिक्री',
    'Today\'s average plan': 'आज का औसत लक्ष्य',
    'Today\'s achievement': 'आज की उपलब्धि',
    'Nepal product sales (lakh)': 'नेपाल उत्पाद बिक्री (लाख)',
    'If you change only the monthly achievement, Other / Range Value adjusts to balance the Nepal product mix. You can also edit the product amounts.': 'यदि आप केवल मासिक उपलब्धि बदलते हैं, तो नेपाल उत्पाद मिश्रण का संतुलन रखने के लिए Other / Range Value समायोजित होगा। आप उत्पाद राशि भी बदल सकते हैं।',
    'Save Nepal figures': 'नेपाल के आँकड़े सहेजें',
    'Dated summary value': 'तारीख़ वाला सारांश मान',
    'Suggested check': 'सुझाई गई जाँच',
    manual: 'मैन्युअल',
    'stock points': 'स्टॉक पॉइंट',
    'No stock points match the filters.': 'फ़िल्टर से मेल खाते स्टॉक पॉइंट नहीं हैं।',
    'No distributors match the filters.': 'फ़िल्टर से मेल खाते वितरक नहीं हैं।',
    'No product stock was found.': 'उत्पाद का स्टॉक नहीं मिला।',
    'Saving Nepal figures…': 'नेपाल के आँकड़े सहेजे जा रहे हैं…',
    'Stock-point balance': 'स्टॉक पॉइंट शेष',
    'CS stock': 'CS स्टॉक',
    'SS stock': 'SS स्टॉक',
    'Stock points': 'स्टॉक पॉइंट',
    'From Item Stock CS & SS Stock': 'Item Stock CS & SS Stock से',
    'Reported separately': 'अलग से रिपोर्ट किया गया',
    'Listed in the Stock sheet': 'Stock शीट में सूचीबद्ध',
    'Daily sales chart': 'दैनिक बिक्री चार्ट',
    'Billing by state or region': 'राज्य या क्षेत्र के अनुसार बिक्री',
    'Overall achievement': 'कुल उपलब्धि',
    'Strongest plan attainment': 'सबसे अच्छी लक्ष्य उपलब्धि',
    'Largest remaining plan balance': 'लक्ष्य की सबसे बड़ी शेष राशि',
    'Largest plan gap': 'लक्ष्य का सबसे बड़ा अंतर',
    'Lowest plan achievement': 'सबसे कम लक्ष्य उपलब्धि',
    'Most zero-billing distributors': 'शून्य बिक्री वाले सबसे अधिक वितरक',
    'Product concentration': 'उत्पाद एकाग्रता',
    'Review what is working in this region and consider whether the approach can be repeated elsewhere.': 'इस क्षेत्र में सफल तरीकों की समीक्षा करें और विचार करें कि क्या उन्हें अन्य जगह दोहराया जा सकता है।',
    'No plan attainment percentage is available.': 'लक्ष्य उपलब्धि प्रतिशत उपलब्ध नहीं है।',
    'Review distributor coverage and follow-up capacity here.': 'यहाँ वितरक कवरेज और अनुवर्ती क्षमता की समीक्षा करें।',
    'Highest count by state / region in the source follow-up list.': 'स्रोत अनुवर्ती सूची में राज्य / क्षेत्र के अनुसार सबसे अधिक संख्या।',
    'Review the account list with the responsible sales representative.': 'खाता सूची की ज़िम्मेदार बिक्री प्रतिनिधि के साथ समीक्षा करें।',
    'Check availability and sales coverage for other product groups.': 'अन्य उत्पाद समूहों की उपलब्धता और बिक्री कवरेज जाँचें।',
    'Check coverage, order frequency, and whether the plan is still appropriate.': 'कवरेज, ऑर्डर की आवृत्ति और लक्ष्य की उपयुक्तता जाँचें।',
    'Review this state’s zero-billing list and confirm the target is current.': 'इस राज्य की शून्य-बिक्री सूची की समीक्षा करें और लक्ष्य की पुष्टि करें।',
    'Current source: —': 'वर्तमान स्रोत: —',
    'No weekly plan workbook is loaded.': 'साप्ताहिक योजना वर्कबुक लोड नहीं है।',
    'No last-year workbook uploaded.': 'पिछले वर्ष की वर्कबुक अपलोड नहीं हुई।',
    'English': 'English',
    'हिन्दी': 'हिन्दी',
    'Sign in': 'साइन इन',
    Username: 'उपयोगकर्ता नाम',
    Password: 'पासवर्ड',
    'Sign in with the owner account to view reports, upload workbooks, and update figures.': 'रिपोर्ट देखने, वर्कबुक अपलोड करने और आँकड़े अपडेट करने के लिए मालिक के खाते से साइन इन करें।',
    'Enter your username and password.': 'अपना उपयोगकर्ता नाम और पासवर्ड दर्ज करें।',
    'The username or password is incorrect.': 'उपयोगकर्ता नाम या पासवर्ड गलत है।',
    'Sign in | Velnik MIS': 'साइन इन | Velnik MIS',
    lakh: 'लाख',
    'NPD stock': 'NPD स्टॉक',
    'The daily chart uses dated Raw transactions; the summary does not provide daily Nepal transaction detail.': 'दैनिक चार्ट तारीख़ वाली Raw प्रविष्टियों पर आधारित है; सारांश में नेपाल के दैनिक लेन-देन का विवरण नहीं है।',
    'Nepal transactions already appear in Raw, so the monthly amount is not added twice.': 'नेपाल के लेन-देन पहले से Raw में हैं, इसलिए मासिक राशि दोबारा नहीं जोड़ी जाती।'
  }));

  const patterns = [
    [/^Latest workbook loaded: (.+)$/, 'नवीनतम वर्कबुक लोड: $1'],
    [/^Latest workbook: (.+) · uploaded (.+)$/, 'नवीनतम वर्कबुक: $1 · अपलोड समय $2'],
    [/^Current source: (.+) · loaded (.+)$/, 'वर्तमान स्रोत: $1 · लोड समय $2'],
    [/^Last loaded: (.+)$/, 'अंतिम बार लोड: $1'],
    [/^Workbook unavailable: (.+)$/, 'वर्कबुक उपलब्ध नहीं: $1'],
    [/^Sales on (.+)$/, '$1 की बिक्री'],
    [/^(.+) active zero-billing distributors$/, '$1 सक्रिय शून्य-बिक्री वितरक'],
    [/^Cannot compare (.+) yet: the uploaded sales workbook does not cover the full previous period \((.+)\)\. Upload a workbook containing those dates\.(.*)$/, 'अभी $1 की तुलना नहीं हो सकती: अपलोड की गई बिक्री वर्कबुक में पिछली पूरी अवधि ($2) शामिल नहीं है। उन तारीख़ों वाली वर्कबुक अपलोड करें।$3'],
    [/^Selected (.+) vs preceding equal-length period (.+)\.(.*)$/, 'चुनी अवधि $1 की तुलना समान लंबाई वाली पिछली अवधि $2 से की गई है।$3'],
    [/^Selected (.+) compared with (.+) from (.+)\.$/, 'चुनी अवधि $1 की तुलना $3 की पिछली अवधि $2 से की गई है।'],
    [/^The uploaded workbook \((.+)\) does not cover the full matching period (.+)\.$/, 'अपलोड की गई वर्कबुक ($1) में पूरी मिलान अवधि $2 शामिल नहीं है।'],
    [/^(.+) · (.+) lakh from dated Raw transactions$/, '$1 · तारीख़ वाली Raw प्रविष्टियों से $2 लाख'],
    [/^(.+) · (.+) lakh total billing · (.+) states? \/ regions?$/, '$1 · कुल बिक्री $2 लाख · $3 राज्य / क्षेत्र'],
    [/^Weekly plan and achievement from (.+)\.$/, '$1 से साप्ताहिक लक्ष्य और उपलब्धि।'],
    [/^(.+) active distributors$/, '$1 सक्रिय वितरक'],
    [/^(.+) stock points$/, '$1 स्टॉक पॉइंट'],
    [/^(.+) products with negative balances$/, '$1 उत्पादों का शेष नकारात्मक है'],
    [/^(.+) achieved\. (.+) active zero-billing distributors are listed in this state \/ region\.$/, '$1 उपलब्धि। इस राज्य / क्षेत्र में शून्य बिक्री वाले $2 सक्रिय वितरक सूचीबद्ध हैं।'],
    [/^Plan (.+) lakh · (.+)%$/, 'लक्ष्य $1 लाख · $2%'],
    [/^(.+) lakh achieved against (.+) lakh planned\.$/, 'योजना $2 लाख के मुकाबले उपलब्धि $1 लाख।'],
    [/^(.+) achieved against (.+) planned\.$/, 'योजना $2 के मुकाबले उपलब्धि $1।'],
    [/^(.+) lakh below plan$/, 'लक्ष्य से $1 लाख कम'],
    [/^(.+) of plan$/, 'लक्ष्य का $1'],
    [/^(.+) of its week plan achieved\. (.+)$/, 'इसके साप्ताहिक लक्ष्य का $1 पूरा हुआ। यहाँ वितरक कवरेज और अनुवर्ती क्षमता की समीक्षा करें।'],
    [/^Billing on (.+)$/, '$1 की बिक्री'],
    [/^Today’s achievement (.+) lakh$/, 'आज की उपलब्धि $1 लाख'],
    [/^Today's achievement (.+) lakh$/, 'आज की उपलब्धि $1 लाख'],
    [/^(.+)% of sales$/, 'बिक्री का $1%'],
    [/^Using “(.+)” and “(.+)” from Without GST\. Sorted by largest remaining gap\.$/, 'GST-रहित शीट के “$1” और “$2” का उपयोग। सबसे बड़े शेष अंतर के अनुसार क्रमबद्ध।'],
    [/^(.+) lakh in the reporting month\.$/, 'रिपोर्टिंग माह में $1 लाख।'],
    [/^Today's achievement (.+) lakh$/, 'आज की उपलब्धि $1 लाख'],
    [/^(.+)% of sales$/, 'बिक्री का $1%'],
    [/^Using “(.+)” and “(.+)” from Without GST\. Sorted by largest remaining gap\.$/, 'GST-रहित शीट के “$1” और “$2” का उपयोग। सबसे बड़े शेष अंतर के अनुसार क्रमबद्ध।'],
    [/^The Without GST sheet shows “(.+)” as its date heading, while Raw transactions end (.+)\. The page uses Raw dates for the report period\.$/, 'GST-रहित शीट में तारीख़ शीर्षक “$1” है, जबकि Raw लेन-देन $2 को समाप्त होते हैं। रिपोर्ट अवधि के लिए पेज Raw तारीख़ों का उपयोग करता है।'],
    [/^(.+) sales lines are missing a Without GST value\.$/, '$1 बिक्री पंक्तियों में GST-रहित राशि उपलब्ध नहीं है।'],
    [/^(.+) lines have a missing or nonnumeric tariff\.$/, '$1 पंक्तियों में टैरिफ़ अनुपलब्ध या गैर-संख्यात्मक है।'],
    [/^(.+) lines share the same voucher, distributor, and item key; review before treating them as duplicates\.$/, '$1 पंक्तियों में वाउचर, वितरक और आइटम कुंजी समान है; डुप्लिकेट मानने से पहले समीक्षा करें।'],
    [/^(.+) state \/ region achievement totals do not match Raw within 0\.02 lakh\. Check the source formulas or exclusions\.$/, '$1 राज्य / क्षेत्र की उपलब्धि का कुल Raw से 0.02 लाख के भीतर मेल नहीं खाता। स्रोत फ़ॉर्मूले या बहिष्करण जाँचें।'],
    [/^State \/ region achievements reconcile with Raw within 0\.02 lakh\.$/, 'राज्य / क्षेत्र की उपलब्धियाँ Raw से 0.02 लाख के भीतर मेल खाती हैं।'],
    [/^(.+) lakh is included in the period total, Nepal state chart, and product mix\. The daily chart uses dated Raw transactions; the summary does not provide daily Nepal transaction detail\.$/, '$1 लाख अवधि कुल, नेपाल राज्य चार्ट और उत्पाद मिश्रण में शामिल है। दैनिक चार्ट तारीख़ वाली Raw प्रविष्टियों पर आधारित है; सारांश में नेपाल के दैनिक लेन-देन का विवरण नहीं है।'],
    [/^(.+) lakh is included in the period total, Nepal state chart, and product mix\.(.*)$/, '$1 लाख अवधि कुल, नेपाल राज्य चार्ट और उत्पाद मिश्रण में शामिल है।$2'],
    [/^Showing (.+)–(.+) of (.+)$/, '$3 में से $1–$2 दिखाए जा रहे हैं'],
    [/^([\d,]+) flagged for follow-up$/, 'अनुवर्ती कार्रवाई के लिए $1 चिह्नित'],
    [/^(\d+) products with negative balances$/, '$1 उत्पादों का शेष नकारात्मक है'],
    [/^Of (.+) sales lines$/, 'कुल बिक्री पंक्तियाँ: $1'],
    [/^With tax from Raw: (.+) lakh$/, 'Raw से कर सहित: $1 लाख'],
    [/^(\d+) product groups · top five account for (\d+)% of sales in this period\.$/, '$1 उत्पाद समूह · शीर्ष पाँच की इस अवधि की बिक्री में हिस्सेदारी $2% है।'],
    [/^(\d+) product groups · top five account for (\d+)% of sales in this period\. Includes Nepal summary product values\.$/, '$1 उत्पाद समूह · शीर्ष पाँच की इस अवधि की बिक्री में हिस्सेदारी $2% है। नेपाल सारांश उत्पाद राशि शामिल है।'],
    [/^Daily sales in lakh$/, 'दैनिक बिक्री (लाख में)'],
    [/^Current source: (.+)$/, 'वर्तमान स्रोत: $1'],
    [/^Uploading (.+)…$/, '$1 अपलोड हो रही है…'],
    [/^No weekly plan is loaded\.$/, 'साप्ताहिक योजना लोड नहीं है।'],
    [/^Could not save Nepal figures: (.+)$/, 'नेपाल के आँकड़े सहेजे नहीं जा सके: $1'],
    [/^The last-year workbook could not be read: (.+)$/, 'पिछले वर्ष की वर्कबुक पढ़ी नहीं जा सकी: $1'],
    [/^Upload the separate FY 2025–26 workbook above to enable this comparison\.$/, 'इस तुलना के लिए ऊपर FY 2025–26 की अलग वर्कबुक अपलोड करें।'],
    [/^(.+): (.+) lakh$/, '$1: $2 लाख'],
    [/^(.+) lakh$/, '$1 लाख']
  ];

  const textStates = new WeakMap();
  const attributeStates = new WeakMap();
  let language = localStorage.getItem('sales-mis-language') === 'hi' ? 'hi' : 'en';

  function translated(source) {
    if (language !== 'hi') return source;
    const exact = translations.get(source.trim());
    if (exact) {
      const start = source.match(/^\s*/)[0];
      const end = source.match(/\s*$/)[0];
      return localizeDates(`${start}${exact}${end}`);
    }
    for (const [pattern, replacement] of patterns) {
      if (pattern.test(source)) return localizeDates(source.replace(pattern, replacement));
    }
    return localizeDates(source);
  }

  function localizeDates(value) {
    const months = {
      Jan: 'जन॰', Feb: 'फ़र॰', Mar: 'मार्च', Apr: 'अप्रै॰', May: 'मई', Jun: 'जून',
      Jul: 'जुल॰', Aug: 'अग॰', Sep: 'सित॰', Sept: 'सित॰', Oct: 'अक्टू॰',
      Nov: 'नव॰', Dec: 'दिस॰'
    };
    return value.replace(/\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b(?=$|\s+\d{4}\b|\s*[–—:,·.])/g,
      (_match, day, month) => `${day} ${months[month]}`);
  }

  function translateText(node) {
    const state = textStates.get(node);
    const source = state && node.data === state.rendered ? state.source : node.data;
    const rendered = translated(source);
    textStates.set(node, { source, rendered });
    if (node.data !== rendered) node.data = rendered;
  }

  function translateAttribute(element, name) {
    let states = attributeStates.get(element);
    if (!states) {
      states = new Map();
      attributeStates.set(element, states);
    }
    const current = element.getAttribute(name);
    const state = states.get(name);
    const source = state && current === state.rendered ? state.source : current;
    const rendered = translated(source);
    states.set(name, { source, rendered });
    if (current !== rendered) element.setAttribute(name, rendered);
  }

  function translateTree(root) {
    if (root.nodeType === Node.TEXT_NODE) {
      translateText(root);
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE && root !== document) return;
    const element = root.nodeType === Node.ELEMENT_NODE ? root : document.documentElement;
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    translateElement(element);
    let node;
    while ((node = walker.nextNode())) {
      if (node.nodeType === Node.TEXT_NODE) translateText(node);
      else translateElement(node);
    }
  }

  function translateElement(element) {
    for (const name of ['placeholder', 'title', 'aria-label']) {
      if (element.hasAttribute(name)) translateAttribute(element, name);
    }
  }

  function applyLanguage() {
    document.documentElement.lang = language;
    document.title = language === 'hi'
      ? (location.pathname === '/login'
        ? 'साइन इन | Velnik MIS'
        : document.getElementById('report-data')
          ? 'वेल्निक MIS | बिक्री विश्लेषण'
          : document.getElementById('billing-data')
            ? 'वेल्निक MIS | बिलिंग दक्षता'
            : 'वेल्निक MIS | स्टॉक रिपोर्ट')
      : (location.pathname === '/login'
        ? 'Sign in | Velnik MIS'
        : document.getElementById('report-data')
          ? 'Velnik MIS | Sales Analysis'
          : document.getElementById('billing-data')
            ? 'Velnik MIS | Billing Efficiency'
            : 'Velnik MIS | Stock Report');
    document.querySelectorAll('#pageLanguageToggle').forEach(button => {
      button.textContent = language === 'hi' ? 'English' : 'हिन्दी';
      button.setAttribute('aria-label', language === 'hi' ? 'Switch page language to English' : 'पेज की भाषा हिंदी में बदलें');
      button.setAttribute('aria-pressed', String(language === 'hi'));
    });
    translateTree(document);
    document.dispatchEvent(new CustomEvent('sales-mis-language-change', {
      detail: { language }
    }));
  }

  const observer = new MutationObserver(records => {
    for (const record of records) {
      if (record.type === 'characterData') {
        translateText(record.target);
      } else if (record.type === 'attributes') {
        translateAttribute(record.target, record.attributeName);
      } else {
        for (const node of record.addedNodes) translateTree(node);
      }
    }
  });
  observer.observe(document.documentElement, {
    subtree: true,
    childList: true,
    characterData: true,
    attributes: true,
    attributeFilter: ['placeholder', 'title', 'aria-label']
  });

  document.addEventListener('click', event => {
    if (!event.target.closest('#pageLanguageToggle')) return;
    language = language === 'hi' ? 'en' : 'hi';
    localStorage.setItem('sales-mis-language', language);
    applyLanguage();
  });

  applyLanguage();
})();
