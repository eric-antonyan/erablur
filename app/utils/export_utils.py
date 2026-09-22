import json
import csv
import os
from datetime import datetime
from io import BytesIO, StringIO
from typing import List, Dict, Any
import xlsxwriter
from loguru import logger

class ExportUtils:
    @staticmethod
    def export_to_json(heroes: List[Dict], filename: str = None) -> BytesIO:
        """Export heroes to JSON format"""
        if not filename:
            filename = f"heroes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
                                 
        export_data = []
        for hero in heroes:
            export_data.append({
                "id": hero.get('id', ''),
                "first_name": hero.get('first_name', ''),
                "last_name": hero.get('last_name', ''),
                "full_name": f"{hero.get('first_name', '')} {hero.get('last_name', '')}",
                "birth_date": hero.get('birth_date', ''),
                "death_date": hero.get('death_date', ''),
                "region": hero.get('region', ''),
                "war": hero.get('war', ''),
                "img_url": hero.get('img_url', ''),
                "bio_link": hero.get('bio_link', ''),
                "bio": hero.get('bio', ''),
                "bio_preview": hero.get('bio', '')[:200] + "..." if len(hero.get('bio', '')) > 200 else hero.get('bio', ''),
                "export_date": datetime.now().isoformat()
            })
        
                                    
        json_buffer = BytesIO()
        json_buffer.write(json.dumps(export_data, ensure_ascii=False, indent=2).encode('utf-8'))
        json_buffer.seek(0)
        
        return json_buffer, filename

    @staticmethod
    def export_to_excel(heroes: List[Dict], filename: str = None) -> BytesIO:
        """Export heroes to Excel format with premium styling"""
        if not filename:
            filename = f"heroes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'options': {'constant_memory': True}})
        
                        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1a3c34',
            'font_color': 'white',
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'top',
            'border': 1,
            'text_wrap': True
        })
        
        centered_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        date_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'num_format': 'yyyy-mm-dd'
        })
        
                              
        summary_sheet = workbook.add_worksheet("Summary")
        summary_sheet.set_column('A:A', 20)
        summary_sheet.set_column('B:B', 30)
        
                          
        summary_data = [
            ["Export Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["Total Heroes", len(heroes)],
            ["Heroes with Bio", len([h for h in heroes if h.get('bio')])],
            ["Heroes with Image", len([h for h in heroes if h.get('img_url')])],
            ["Unique Wars", len(set(h.get('war', '') for h in heroes if h.get('war')))],
            ["Unique Regions", len(set(h.get('region', '') for h in heroes if h.get('region')))]
        ]
        
        for row, (key, value) in enumerate(summary_data):
            summary_sheet.write(row, 0, key, header_format)
            summary_sheet.write(row, 1, value, cell_format)
        
                             
        heroes_sheet = workbook.add_worksheet("Heroes")
        
                        
        columns = [
            {"header": "ID", "width": 36},
            {"header": "First Name", "width": 20},
            {"header": "Last Name", "width": 20},
            {"header": "Full Name", "width": 30},
            {"header": "Birth Date", "width": 15},
            {"header": "Death Date", "width": 15},
            {"header": "Region", "width": 25},
            {"header": "War", "width": 25},
            {"header": "Image URL", "width": 40},
            {"header": "Bio Link", "width": 40},
            {"header": "Bio Preview", "width": 50}
        ]
        
                       
        for col, col_data in enumerate(columns):
            heroes_sheet.write(0, col, col_data["header"], header_format)
            heroes_sheet.set_column(col, col, col_data["width"])
        
                    
        for row, hero in enumerate(heroes, start=1):
            heroes_sheet.write(row, 0, hero.get('id', ''), cell_format)
            heroes_sheet.write(row, 1, hero.get('first_name', ''), cell_format)
            heroes_sheet.write(row, 2, hero.get('last_name', ''), cell_format)
            heroes_sheet.write(row, 3, f"{hero.get('first_name', '')} {hero.get('last_name', '')}", cell_format)
            heroes_sheet.write(row, 4, hero.get('birth_date', ''), centered_format)
            heroes_sheet.write(row, 5, hero.get('death_date', ''), centered_format)
            heroes_sheet.write(row, 6, hero.get('region', ''), cell_format)
            heroes_sheet.write(row, 7, hero.get('war', ''), cell_format)
            heroes_sheet.write(row, 8, hero.get('img_url', ''), cell_format)
            heroes_sheet.write(row, 9, hero.get('bio_link', ''), cell_format)
            
                         
            bio = hero.get('bio', '')
            bio_preview = bio[:200] + "..." if len(bio) > 200 else bio
            heroes_sheet.write(row, 10, bio_preview, cell_format)
        
                              
        stats_sheet = workbook.add_worksheet("Statistics")
        stats_sheet.set_column('A:A', 25)
        stats_sheet.set_column('B:B', 20)
        stats_sheet.set_column('C:C', 15)
        
                        
        war_stats = {}
        for hero in heroes:
            war = hero.get('war', 'Unknown')
            war_stats[war] = war_stats.get(war, 0) + 1
        
        stats_sheet.write(0, 0, "War Statistics", header_format)
        stats_sheet.write(1, 0, "War", header_format)
        stats_sheet.write(1, 1, "Count", header_format)
        stats_sheet.write(1, 2, "Percentage", header_format)
        
        row = 2
        for war, count in sorted(war_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(heroes)) * 100
            stats_sheet.write(row, 0, war, cell_format)
            stats_sheet.write(row, 1, count, centered_format)
            stats_sheet.write(row, 2, f"{percentage:.1f}%", centered_format)
            row += 1
        
                           
        region_stats = {}
        for hero in heroes:
            region = hero.get('region', 'Unknown')
            region_stats[region] = region_stats.get(region, 0) + 1
        
        stats_sheet.write(row + 2, 0, "Region Statistics", header_format)
        stats_sheet.write(row + 3, 0, "Region", header_format)
        stats_sheet.write(row + 3, 1, "Count", header_format)
        stats_sheet.write(row + 3, 2, "Percentage", header_format)
        
        row = row + 4
        for region, count in sorted(region_stats.items(), key=lambda x: x[1], reverse=True)[:20]:
            percentage = (count / len(heroes)) * 100
            stats_sheet.write(row, 0, region, cell_format)
            stats_sheet.write(row, 1, count, centered_format)
            stats_sheet.write(row, 2, f"{percentage:.1f}%", centered_format)
            row += 1
        
        workbook.close()
        output.seek(0)
        return output, filename

    @staticmethod
    def export_to_html(heroes: List[Dict], filename: str = None) -> str:
        """Export heroes to premium HTML report"""
        if not filename:
            filename = f"heroes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
                              
        total_heroes = len(heroes)
        heroes_with_bio = len([h for h in heroes if h.get('bio')])
        heroes_with_image = len([h for h in heroes if h.get('img_url')])
        unique_wars = len(set(h.get('war', '') for h in heroes if h.get('war')))
        unique_regions = len(set(h.get('region', '') for h in heroes if h.get('region')))
        
                              
        wars = sorted(set(h.get('war', '') for h in heroes if h.get('war')))
        war_options = ""
        for war in wars:
            war_options += f'<option value="{war}">{war}</option>'
        
                                 
        regions = sorted(set(h.get('region', '') for h in heroes if h.get('region')))
        region_options = ""
        for region in regions:
            region_options += f'<option value="{region}">{region}</option>'
        
                             
        table_rows = ""
        for idx, hero in enumerate(heroes[:100], 1):
            first_name = hero.get('first_name', '')
            last_name = hero.get('last_name', '')
            birth_date = hero.get('birth_date', '')
            death_date = hero.get('death_date', '')
            region = hero.get('region', '')
            war = hero.get('war', '')
            bio = hero.get('bio', '')
            bio_preview = bio[:100] + "..." if len(bio) > 100 else bio
            
            table_rows += f'''
            <tr>
                <td>{idx}</td>
                <td>{first_name}</td>
                <td>{last_name}</td>
                <td>{birth_date}</td>
                <td>{death_date}</td>
                <td><span class="badge badge-region">{region}</span></td>
                <td><span class="badge badge-war">{war}</span></td>
                <td>{bio_preview}</td>
            </tr>
            '''
        
                       
        html_content = f'''<!DOCTYPE html>
    <html lang="hy">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Հայ Հերոսների Թանգարան - Export Report</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', 'Arial', 'Noto Sans Armenian', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #1a3c34 0%, #2d5a4c 100%);
                color: white;
                padding: 40px;
                text-align: center;
                position: relative;
            }}
            
            .header h1 {{
                font-size: 2.5em;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            }}
            
            .header .subtitle {{
                font-size: 1.1em;
                opacity: 0.95;
            }}
            
            .header .date {{
                position: absolute;
                bottom: 20px;
                right: 30px;
                font-size: 0.9em;
                opacity: 0.8;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                padding: 40px;
                background: #f8f9fa;
            }}
            
            .stat-card {{
                background: white;
                border-radius: 15px;
                padding: 25px;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                transition: transform 0.3s, box-shadow 0.3s;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0,0,0,0.15);
            }}
            
            .stat-icon {{
                font-size: 3em;
                margin-bottom: 15px;
            }}
            
            .stat-value {{
                font-size: 2.5em;
                font-weight: bold;
                color: #1a3c34;
                margin-bottom: 5px;
            }}
            
            .stat-label {{
                font-size: 1em;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .filters {{
                padding: 20px 40px;
                background: white;
                border-bottom: 2px solid #e0e0e0;
            }}
            
            .filter-group {{
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
                align-items: center;
            }}
            
            .filter-group input,
            .filter-group select {{
                padding: 10px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 14px;
                transition: border-color 0.3s;
            }}
            
            .filter-group input:focus,
            .filter-group select:focus {{
                outline: none;
                border-color: #1a3c34;
            }}
            
            .btn {{
                padding: 10px 20px;
                background: linear-gradient(135deg, #1a3c34 0%, #2d5a4c 100%);
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                transition: transform 0.2s;
            }}
            
            .btn:hover {{
                transform: scale(1.05);
            }}
            
            .table-container {{
                padding: 20px 40px 40px 40px;
                overflow-x: auto;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            
            th {{
                background: linear-gradient(135deg, #1a3c34 0%, #2d5a4c 100%);
                color: white;
                padding: 15px;
                text-align: left;
                font-weight: 600;
                cursor: pointer;
                user-select: none;
            }}
            
            th:hover {{
                background: linear-gradient(135deg, #2d5a4c 0%, #3d7a64 100%);
            }}
            
            td {{
                padding: 12px 15px;
                border-bottom: 1px solid #e0e0e0;
            }}
            
            tr:hover {{
                background: #f5f5f5;
            }}
            
            .badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
            }}
            
            .badge-war {{
                background: #ff6b6b;
                color: white;
            }}
            
            .badge-region {{
                background: #4ecdc4;
                color: white;
            }}
            
            .footer {{
                background: #2c3e50;
                color: white;
                padding: 30px;
                text-align: center;
            }}
            
            .export-buttons {{
                display: flex;
                gap: 10px;
                justify-content: flex-end;
                padding: 20px 40px;
                background: #f8f9fa;
            }}
            
            @media (max-width: 768px) {{
                .stats-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .filter-group {{
                    flex-direction: column;
                }}
                
                th, td {{
                    font-size: 12px;
                    padding: 8px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🇦🇲 Հայ Հերոսների Թանգարան</h1>
                <div class="subtitle">Հերոսների ամբողջական տվյալների հաշվետվություն</div>
                <div class="date">Տպագրված: {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}</div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">🦸</div>
                    <div class="stat-value">{total_heroes}</div>
                    <div class="stat-label">Ընդհանուր Հերոսներ</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📝</div>
                    <div class="stat-value">{heroes_with_bio}</div>
                    <div class="stat-label">Կենսագրությամբ</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🖼️</div>
                    <div class="stat-value">{heroes_with_image}</div>
                    <div class="stat-label">Նկարով</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">⚔️</div>
                    <div class="stat-value">{unique_wars}</div>
                    <div class="stat-label">Մարտեր</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📍</div>
                    <div class="stat-value">{unique_regions}</div>
                    <div class="stat-label">Մարզեր</div>
                </div>
            </div>
            
            <div class="export-buttons">
                <button class="btn" onclick="window.location.href='/export_excel'">📊 Export to Excel</button>
                <button class="btn" onclick="window.location.href='/export_json'">📄 Export to JSON</button>
                <button class="btn" onclick="window.print()">🖨️ Print Report</button>
            </div>
            
            <div class="filters">
                <div class="filter-group">
                    <input type="text" id="searchInput" placeholder="🔍 Որոնել անունով, ազգանունով..." onkeyup="filterTable()">
                    <select id="warFilter" onchange="filterTable()">
                        <option value="">Բոլոր մարտերը</option>
                        {war_options}
                    </select>
                    <select id="regionFilter" onchange="filterTable()">
                        <option value="">Բոլոր մարզերը</option>
                        {region_options}
                    </select>
                    <button class="btn" onclick="resetFilters()">🔄 Reset Filters</button>
                </div>
            </div>
            
            <div class="table-container">
                <table id="heroesTable">
                    <thead>
                        <tr>
                            <th onclick="sortTable(0)">#</th>
                            <th onclick="sortTable(1)">Անուն</th>
                            <th onclick="sortTable(2)">Ազգանուն</th>
                            <th onclick="sortTable(3)">Ծննդյան թիվ</th>
                            <th onclick="sortTable(4)">Մահվան թիվ</th>
                            <th onclick="sortTable(5)">Մարզ</th>
                            <th onclick="sortTable(6)">Մարտ</th>
                            <th onclick="sortTable(7)">Կենսագրություն</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody">
                        {table_rows}
                    </tbody>
                </table>
            </div>
            
            <div class="footer">
                <p>© 2024 Հայ Հերոսների Թանգարան | Պահպանենք մեր հերոսների հիշատակը</p>
                <p style="margin-top: 10px; font-size: 12px;">Տվյալները թարմացված են {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </div>
        
        <script>
            function filterTable() {{
                const searchInput = document.getElementById('searchInput').value.toLowerCase();
                const warFilter = document.getElementById('warFilter').value;
                const regionFilter = document.getElementById('regionFilter').value;
                const table = document.getElementById('heroesTable');
                const rows = table.getElementsByTagName('tr');
                
                for (let i = 1; i < rows.length; i++) {{
                    const cells = rows[i].getElementsByTagName('td');
                    if (cells.length > 0) {{
                        const firstName = cells[1]?.textContent.toLowerCase() || '';
                        const lastName = cells[2]?.textContent.toLowerCase() || '';
                        const war = cells[6]?.textContent || '';
                        const region = cells[5]?.textContent || '';
                        
                        const matchesSearch = firstName.includes(searchInput) || lastName.includes(searchInput);
                        const matchesWar = !warFilter || war === warFilter;
                        const matchesRegion = !regionFilter || region === regionFilter;
                        
                        rows[i].style.display = (matchesSearch && matchesWar && matchesRegion) ? '' : 'none';
                    }}
                }}
            }}
            
            let sortDirection = {{}};
            
            function sortTable(columnIndex) {{
                const table = document.getElementById('heroesTable');
                const tbody = table.getElementsByTagName('tbody')[0];
                const rows = Array.from(tbody.getElementsByTagName('tr'));
                
                sortDirection[columnIndex] = !sortDirection[columnIndex];
                const direction = sortDirection[columnIndex] ? 1 : -1;
                
                rows.sort((a, b) => {{
                    const aValue = a.getElementsByTagName('td')[columnIndex]?.textContent || '';
                    const bValue = b.getElementsByTagName('td')[columnIndex]?.textContent || '';
                    return aValue.localeCompare(bValue, 'hy') * direction;
                }});
                
                rows.forEach(row => tbody.appendChild(row));
            }}
            
            function resetFilters() {{
                document.getElementById('searchInput').value = '';
                document.getElementById('warFilter').value = '';
                document.getElementById('regionFilter').value = '';
                filterTable();
            }}
        </script>
    </body>
    </html>'''
        
                        
        os.makedirs("data/exports", exist_ok=True)
        html_path = os.path.join("data", "exports", filename)
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_path

export_utils = ExportUtils()