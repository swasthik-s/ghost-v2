#property strict
#property version "0.2.0"
#property description "GHOST read-only MT5 telemetry exporter. Does not place or modify orders."

input int InpExportIntervalSeconds = 1;
input bool InpExportAllAccountPositions = true;
input long InpMagicFilter = 0; // 0 = all positions; otherwise matching magic only

string JsonEscape(const string value)
{
   string out = "";
   for(int i = 0; i < StringLen(value); i++)
   {
      ushort ch = StringGetCharacter(value, i);
      if(ch == 34) out += "\\\"";
      else if(ch == 92) out += "\\\\";
      else if(ch == 10) out += "\\n";
      else if(ch == 13) out += "\\r";
      else if(ch == 9) out += "\\t";
      else out += ShortToString(ch);
   }
   return out;
}

string Number(const double value, const int digits = 2)
{
   return DoubleToString(value, digits);
}

bool ExportSnapshot()
{
   FolderCreate("GHOST", FILE_COMMON);
   string path = "GHOST\\telemetry.json";
   int handle = FileOpen(path, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(handle == INVALID_HANDLE)
   {
      Print("GHOST exporter: FileOpen failed. Error=", GetLastError());
      return false;
   }

   string server = AccountInfoString(ACCOUNT_SERVER);
   string company = AccountInfoString(ACCOUNT_COMPANY);
   string currency = AccountInfoString(ACCOUNT_CURRENCY);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double floating = AccountInfoDouble(ACCOUNT_PROFIT);

   string json = "{";
   json += "\"schema_version\":1,";
   json += "\"generated_at_utc\":\"" + TimeToString(TimeGMT(), TIME_DATE | TIME_SECONDS) + "\",";
   json += "\"terminal\":{";
   json += "\"connected\":" + (TerminalInfoInteger(TERMINAL_CONNECTED) ? "true" : "false") + ",";
   json += "\"company\":\"" + JsonEscape(company) + "\",";
   json += "\"server\":\"" + JsonEscape(server) + "\",";
   json += "\"build\":" + IntegerToString((int)TerminalInfoInteger(TERMINAL_BUILD));
   json += "},";
   json += "\"account\":{";
   json += "\"currency\":\"" + JsonEscape(currency) + "\",";
   json += "\"balance\":" + Number(AccountInfoDouble(ACCOUNT_BALANCE)) + ",";
   json += "\"equity\":" + Number(AccountInfoDouble(ACCOUNT_EQUITY)) + ",";
   json += "\"floating_pnl\":" + Number(floating) + ",";
   json += "\"margin\":" + Number(AccountInfoDouble(ACCOUNT_MARGIN)) + ",";
   json += "\"free_margin\":" + Number(AccountInfoDouble(ACCOUNT_MARGIN_FREE)) + ",";
   json += "\"margin_level\":" + Number(AccountInfoDouble(ACCOUNT_MARGIN_LEVEL));
   json += "},";
   json += "\"positions\":[";

   bool first = true;
   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(!InpExportAllAccountPositions && InpMagicFilter != 0 && magic != InpMagicFilter)
         continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      string comment = PositionGetString(POSITION_COMMENT);
      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      int symbolDigits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
      if(!first) json += ",";
      first = false;
      json += "{";
      json += "\"ticket\":" + IntegerToString((long)ticket) + ",";
      json += "\"symbol\":\"" + JsonEscape(symbol) + "\",";
      json += "\"side\":\"" + (type == POSITION_TYPE_BUY ? "BUY" : "SELL") + "\",";
      json += "\"volume\":" + Number(PositionGetDouble(POSITION_VOLUME), 2) + ",";
      json += "\"price_open\":" + Number(PositionGetDouble(POSITION_PRICE_OPEN), symbolDigits) + ",";
      json += "\"price_current\":" + Number(PositionGetDouble(POSITION_PRICE_CURRENT), symbolDigits) + ",";
      json += "\"profit\":" + Number(PositionGetDouble(POSITION_PROFIT)) + ",";
      json += "\"swap\":" + Number(PositionGetDouble(POSITION_SWAP)) + ",";
      json += "\"stop_loss\":" + Number(PositionGetDouble(POSITION_SL), symbolDigits) + ",";
      json += "\"take_profit\":" + Number(PositionGetDouble(POSITION_TP), symbolDigits) + ",";
      json += "\"magic\":" + IntegerToString(magic) + ",";
      json += "\"comment\":\"" + JsonEscape(comment) + "\"";
      json += "}";
   }
   json += "]}";

   uint written = FileWriteString(handle, json);
   FileClose(handle);
   if(written == 0)
   {
      Print("GHOST exporter: failed to write telemetry JSON.");
      return false;
   }
   return true;
}

int OnInit()
{
   if(InpExportIntervalSeconds < 1)
      return INIT_PARAMETERS_INCORRECT;
   EventSetTimer(InpExportIntervalSeconds);
   Print("GHOST read-only telemetry exporter initialized. Orders are not enabled.");
   ExportSnapshot();
   return INIT_SUCCEEDED;
}

void OnTimer()
{
   ExportSnapshot();
}

void OnTick()
{
   // Intentionally empty. Telemetry only.
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ExportSnapshot();
}
