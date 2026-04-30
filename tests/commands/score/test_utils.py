from sufe_cli.commands.score.utils import parse_summary, parse_courses


SAMPLE_HTML = """\
<html><body>
<table class="gridtable">
  <thead class="gridhead">
    <tr><th>学年度</th><th>学期</th><th>门数</th><th>平均成绩</th><th>总学分</th><th>平均绩点</th></tr>
  </thead>
  <tbody>
    <tr class="griddata-even">
      <td>2023-2024</td><td>1</td>
      <td>9<input type="hidden" class="count" value="9"></td>
      <td>86.2</td><td>25</td><td>3.54</td>
    </tr>
    <tr class="griddata-odd">
      <td>2023-2024</td><td>2</td>
      <td>12<input type="hidden" class="count" value="12"></td>
      <td>90.24</td><td>29</td><td>3.77</td>
    </tr>
    <tr class="griddata-odd">
      <th colspan="2">在校汇总</th>
      <th><span id="all_count">50</span></th>
      <th>89.27</th><th>124</th><th>3.73</th>
    </tr>
    <tr class="griddata-even">
      <th colspan="6" align="right">统计时间:2026-05-01 02:01</th>
    </tr>
  </tbody>
</table>

<table id="grid21344342991" class="gridtable">
  <thead class="gridhead">
    <tr>
      <th>学年学期</th><th>课程代码</th><th>课程序号</th>
      <th>课程名称</th><th>课程类别</th><th>学分</th>
      <th>总评成绩</th><th>最终</th><th>绩点</th>
    </tr>
  </thead>
  <tbody id="grid21344342991_data">
    <tr class="griddata-even">
      <td>2025-2026 1</td><td>102041</td><td>1135</td>
      <td>财政学</td><td>选修课</td><td>2</td>
      <td style="">97</td><td style="">97</td><td>4</td>
    </tr>
    <tr class="griddata-odd">
      <td>2025-2026 1</td><td>103432</td><td>0821</td>
      <td>金融中国-通识篇</td><td>通识模块四（经济分析与数学思维）限选课</td><td>2</td>
      <td style="">80</td><td style="">80</td><td>3</td>
    </tr>
    <tr class="griddata-even">
      <td>2024-2025 2</td><td>102876</td><td>1078</td>
      <td>深度学习</td><td>选修课</td><td>3</td>
      <td style="">99</td><td style="">99</td><td>4</td>
    </tr>
  </tbody>
</table>
</body></html>
"""


class TestParseSummary:
    def test_basic_parse(self) -> None:
        headers, rows = parse_summary(SAMPLE_HTML)

        assert headers == ["学年度", "学期", "门数", "平均成绩", "总学分", "平均绩点"]
        assert len(rows) == 2

        assert rows[0] == ["2023-2024", "1", "9", "86.2", "25", "3.54"]
        assert rows[1] == ["2023-2024", "2", "12", "90.24", "29", "3.77"]

    def test_skips_summary_and_time_rows(self) -> None:
        """汇总行（含 th colspan）和统计时间行应该被跳过"""
        _, rows = parse_summary(SAMPLE_HTML)
        # 只有 2 条数据行，汇总行和时间行被跳过
        assert len(rows) == 2
        assert all(len(r) == 6 for r in rows)

    def test_empty_html(self) -> None:
        headers, rows = parse_summary("<html></html>")
        assert headers == []
        assert rows == []

    def test_no_table(self) -> None:
        headers, rows = parse_summary("<html><body><p>no table</p></body></html>")
        assert headers == []
        assert rows == []


class TestParseCourses:
    def test_basic_parse(self) -> None:
        headers, rows = parse_courses(SAMPLE_HTML)

        assert headers == [
            "学年学期",
            "课程代码",
            "课程序号",
            "课程名称",
            "课程类别",
            "学分",
            "总评成绩",
            "最终",
            "绩点",
        ]
        assert len(rows) == 3

        assert rows[0] == ["2025-2026 1", "102041", "1135", "财政学", "选修课", "2", "97", "97", "4"]
        assert rows[1] == [
            "2025-2026 1",
            "103432",
            "0821",
            "金融中国-通识篇",
            "通识模块四（经济分析与数学思维）限选课",
            "2",
            "80",
            "80",
            "3",
        ]
        assert rows[2] == ["2024-2025 2", "102876", "1078", "深度学习", "选修课", "3", "99", "99", "4"]

    def test_strips_whitespace_and_style(self) -> None:
        """td 中的 style 属性和多余空白应被清理"""
        _, rows = parse_courses(SAMPLE_HTML)
        for row in rows:
            for cell in row:
                assert cell == cell.strip()
                assert "style" not in cell.lower()

    def test_empty_html(self) -> None:
        headers, rows = parse_courses("<html></html>")
        assert headers == []
        assert rows == []

    def test_no_table(self) -> None:
        headers, rows = parse_courses("<html><body><p>no table</p></body></html>")
        assert headers == []
        assert rows == []

    def test_no_tbody(self) -> None:
        html = '<html><body><table id="grid21344342991"><tr><td>1</td></tr></table></body></html>'
        headers, rows = parse_courses(html)
        assert headers == []
        assert rows == []
