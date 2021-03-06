import { BrowserModule } from '@angular/platform-browser';
import { NgModule, OnInit } from '@angular/core';
import { AppMaterialModule } from './app.material';
import { FlexLayoutModule } from '@angular/flex-layout';
import {HttpClientModule} from '@angular/common/http';

import { AppComponent } from './app.component';
import { HeaderComponent } from './header/header.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { UniversalCoreComponent } from './dashboard/universal-core/universal-core.component';
import { StatisticsComponent } from './dashboard/statistics/statistics.component';
import { ReportDataService } from './report-data.service';
import { KeysPipe } from './keys.pipe';
import { SystemInformationComponent } from './dashboard/system-information/system-information.component';
import { AccordionComponent } from './accordion/accordion.component';
import { ResultButtonComponent } from './result-button/result-button.component';
import { DiffButtonComponent } from './diff-button/diff-button.component';
import {TauChartHistoryComponent} from './tauchart-history/tauchart-history.component';
import {TauChartBarComponent} from './tauchart-bar/tauchart-bar.component';
import { HelpDialogComponent, HelpDialogTextComponent} from './help-dialog/help-dialog.component';
import { ScoreFormulaComponent } from './score-formula/score-formula.component';


@NgModule({
  declarations: [
    AppComponent,
    HeaderComponent,
    DashboardComponent,
    UniversalCoreComponent,
    StatisticsComponent,
    KeysPipe,
    SystemInformationComponent,
    AccordionComponent,
    ResultButtonComponent,
    DiffButtonComponent,
    TauChartHistoryComponent,
    TauChartBarComponent,
    HelpDialogComponent,
    HelpDialogTextComponent,
    ScoreFormulaComponent
  ],
  imports: [
    BrowserModule,
    AppMaterialModule,
    FlexLayoutModule,
    HttpClientModule,
  ],
  exports: [
    BrowserModule,
    AppMaterialModule
  ],
  entryComponents: [HelpDialogComponent, HelpDialogTextComponent],
  providers: [ReportDataService],
  bootstrap: [AppComponent]
})
export class AppModule implements OnInit {

  constructor(private reportDataService: ReportDataService) {
    this.reportDataService.loadResults();
  }

  ngOnInit() {

  }
}
